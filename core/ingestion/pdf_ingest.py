import hashlib
import json
import os
import re
import shutil
import signal
from pathlib import Path
from typing import Callable, Optional

import fitz  # PyMuPDF
import lancedb

from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings

from core import config
from core.storage import clear_all, init_db, insert_chunk, insert_document
from core.utils import extract_waiver_info, parse_effective_date


class TimeoutException(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutException()


def _get_file_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_embedder(provider: str):
    if provider.upper() == "OPENAI":
        return OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL)
    return OllamaEmbeddings(model=config.OLLAMA_EMBEDDING_MODEL)


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "unknown"


def _build_upload_path(state: str, waiver_number: str, approved_date, filename: str) -> Path:
    ext = Path(filename).suffix or ".pdf"
    state_folder = state or "unknown_state"
    waiver_name = _slugify(waiver_number) if waiver_number else "unknown_waiver"
    date_part = approved_date.strftime("%Y-%m-%d") if approved_date else "no_date"
    new_filename = f"{waiver_name}_{date_part}{ext}".upper()
    return config.UPLOADS_DIR / state_folder / new_filename


def ingest_pdf_folder(
    data_folder: str,
    provider: str,
    timeout_seconds: int = 60,
    persist_tracking: bool = True,
    clear_existing: bool = True,
    on_progress: Optional[Callable[[dict], None]] = None,
) -> dict:
    """
    Scan a folder for PDFs, extract metadata, persist local SQLite, and index LanceDB.
    Returns a summary dict with counts.
    """
    data_path = Path(data_folder).resolve()
    db_path = str(config.LANCE_DB_PATH)
    state_to_code = {name.lower(): code for code, name in config.US_STATES}

    if not data_path.exists():
        raise FileNotFoundError(f"Folder not found: {data_path}")

    init_db()
    config.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    config.LANCE_DB_PATH.mkdir(parents=True, exist_ok=True)

    db = lancedb.connect(str(config.LANCE_DB_PATH))
    if "policy_docs" in db.table_names():
        db.drop_table("policy_docs")

    if clear_existing:
        clear_all()

    track_path = config.BASE_DIR / "indexed_files.json"
    indexed_data = json.loads(track_path.read_text()) if track_path.exists() else {}

    embedder = _get_embedder(provider)

    signal.signal(signal.SIGALRM, _timeout_handler)

    processed = 0
    skipped = 0
    failed = 0

    for pdf_path in data_path.rglob("*.pdf"):
        rel_path = str(pdf_path.relative_to(data_path))
        file_hash = _get_file_hash(pdf_path)

        if indexed_data.get(rel_path) == file_hash:
            skipped += 1
            if on_progress:
                on_progress({"event": "skip", "path": rel_path})
            continue

        try:
            signal.alarm(timeout_seconds)

            metadata = extract_waiver_info(str(pdf_path))
            state_code = state_to_code.get(metadata.get("State", "").lower())
            waiver_num = metadata.get("Waiver Number")

            if not state_code or not waiver_num:
                skipped += 1
                if on_progress:
                    on_progress({"event": "skip_missing_metadata", "path": rel_path})
                continue

            exclude_keys = {
                "Program Title",
                "Waiver Number",
                "State",
                "Approved Effective Date",
                "Amendment Number",
            }
            extra_metadata = {k: v for k, v in metadata.items() if k not in exclude_keys}

            approved_date = parse_effective_date(metadata.get("Approved Effective Date") or "")
            stored_path = _build_upload_path(state_code, waiver_num, approved_date, pdf_path.name)
            stored_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pdf_path, stored_path)

            doc_id = insert_document(
                source_path=rel_path,
                stored_path=str(stored_path.relative_to(config.BASE_DIR)),
                state=state_code,
                application_number=waiver_num,
                program_title=metadata.get("Program Title"),
                application_type=("AMENDMENT" if metadata.get("Amendment Number") else "NEW"),
                approved_effective_date=approved_date.isoformat() if approved_date else None,
                year=approved_date.year if approved_date else None,
                extra=extra_metadata,
            )

            doc_vector_buffer: list[Document] = []
            with fitz.open(pdf_path) as doc_pdf:
                for i, page in enumerate(doc_pdf):
                    text = page.get_text("text").strip()
                    if not text:
                        continue

                    chunk_id = insert_chunk(
                        document_id=doc_id,
                        text=text,
                        page=i + 1,
                        order_index=i,
                    )
                    doc_vector_buffer.append(
                        Document(
                            page_content=text,
                            metadata={
                                "chunk_id": chunk_id,
                                "doc_id": doc_id,
                                "state": state_code,
                                "source_path": rel_path,
                                "page": i + 1,
                            },
                        )
                    )

            signal.alarm(0)

            if doc_vector_buffer:
                table_mode = "overwrite" if "policy_docs" not in db.table_names() else "append"
                LanceDB.from_documents(
                    doc_vector_buffer,
                    embedder,
                    uri=db_path,
                    table_name="policy_docs",
                    mode=table_mode,
                )

            indexed_data[rel_path] = file_hash
            processed += 1
            if on_progress:
                on_progress({"event": "processed", "path": rel_path})

        except TimeoutException:
            skipped += 1
            if on_progress:
                on_progress({"event": "timeout", "path": rel_path})
            signal.alarm(0)
            continue
        except Exception as exc:
            failed += 1
            if on_progress:
                on_progress({"event": "error", "path": rel_path, "error": str(exc)})

    if persist_tracking:
        track_path.write_text(json.dumps(indexed_data, indent=2))
    elif track_path.exists():
        os.remove(track_path)

    return {
        "processed": processed,
        "skipped": skipped,
        "failed": failed,
        "total": processed + skipped + failed,
    }
