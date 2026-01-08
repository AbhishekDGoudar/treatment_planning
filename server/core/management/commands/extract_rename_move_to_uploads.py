import os
import hashlib
import json
import fitz  # PyMuPDF
import signal
from pathlib import Path
import lancedb

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from django.db import transaction

# Models & Utils
from core.models import WaiverDocument, Chunk, Embedding, US_STATES
from core.utils import extract_waiver_info, parse_effective_date

# Vector DB & Embeddings
from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_openai import OpenAIEmbeddings


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException()


def get_file_hash(file_path: Path) -> str:
    hasher = hashlib.md5()
    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


class Command(BaseCommand):
    help = (
        "Scans data folder (recursively), extracts metadata, creates Waiver models, "
        "populates LanceDB, and skips files that take > 60 seconds."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--folder",
            type=str,
            default="./data/",
            help="Folder to scan for PDFs (recursive)",
        )

    def handle(self, *args, **options):
        provider = settings.AI_PROVIDER
        data_folder = Path(options["folder"]).resolve()
        db_path = str(settings.LANCE_DB_PATH)
        state_to_code = {name.lower(): code for code, name in US_STATES}

        db = lancedb.connect(settings.LANCE_DB_PATH)
        if "policy_docs" in db.table_names():
            db.drop_table("policy_docs")

        # ⚠️ Destructive
        WaiverDocument.objects.all().delete()
        Embedding.objects.all().delete()
        Chunk.objects.all().delete()

        track_path = Path(settings.BASE_DIR) / "indexed_files.json"
        indexed_data = json.loads(track_path.read_text()) if track_path.exists() else {}

        embedder = (
            OpenAIEmbeddings(model=settings.OLLAMA_EMBEDDING_MODEL)
            if provider.upper() == "OPENAI"
            else OllamaEmbeddings(model=settings.OLLAMA_EMBEDDING_MODEL)
        )

        if not data_folder.exists():
            self.stderr.write(f"Folder not found: {data_folder}")
            return

        # Set up the timeout signal
        signal.signal(signal.SIGALRM, timeout_handler)

        # Recursive scan
        for pdf_path in data_folder.rglob("*.pdf"):
            rel_path = str(pdf_path.relative_to(data_folder))
            file_hash = get_file_hash(pdf_path)

            if indexed_data.get(rel_path) == file_hash:
                self.stdout.write(f"⏩ Already indexed: {rel_path}")
                continue

            try:
                # Start 60s timer
                signal.alarm(60)

                with transaction.atomic():
                    metadata = extract_waiver_info(str(pdf_path))
                    state_code = state_to_code.get(metadata.get("State", "").lower())
                    waiver_num = metadata.get("Waiver Number")

                    if not state_code or not waiver_num:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ Skipping (missing metadata): {rel_path}"
                            )
                        )
                        continue

                    # Cleanup old records
                    WaiverDocument.objects.filter(application_number=waiver_num).delete()

                    # Extra metadata
                    exclude_keys = {
                        "Program Title",
                        "Waiver Number",
                        "State",
                        "Approved Effective Date",
                        "Amendment Number",
                    }
                    extra_metadata = {k: v for k, v in metadata.items() if k not in exclude_keys}

                    approved_date = parse_effective_date(metadata.get("Approved Effective Date") or "")

                    # Create document
                    waiver_doc = WaiverDocument.objects.create(
                        program_title=metadata.get("Program Title"),
                        application_number=waiver_num,
                        application_type=("AMENDMENT" if metadata.get("Amendment Number") else "NEW"),
                        state=state_code,
                        approved_effective_date=approved_date,
                        year=approved_date.year if approved_date else None,
                        extra=extra_metadata,
                    )

                    with pdf_path.open("rb") as f:
                        waiver_doc.file_path.save(pdf_path.name, File(f), save=True)

                    # Page-level chunking
                    doc_vector_buffer: list[Document] = []
                    with fitz.open(pdf_path) as doc_pdf:
                        for i, page in enumerate(doc_pdf):
                            text = page.get_text("text").strip()
                            if not text:
                                continue

                            chunk_obj = Chunk.objects.create(
                                document=waiver_doc,
                                text=text,
                                page=i + 1,
                                order=i,
                            )
                            Embedding.objects.create(
                                kind="text",
                                vector_id=0,
                                chunk=chunk_obj,
                                document=waiver_doc,
                            )
                            doc_vector_buffer.append(
                                Document(
                                    page_content=text,
                                    metadata={
                                        "django_chunk_id": chunk_obj.id,
                                        "doc_id": waiver_doc.id,
                                        "state": state_code,
                                        "source_path": rel_path,
                                        "page": i + 1,
                                    },
                                )
                            )

                # Cancel alarm after successful processing
                signal.alarm(0)

                # Sync LanceDB per document
                if doc_vector_buffer:
                    table_mode = "overwrite" if not Path(db_path).exists() else "append"
                    LanceDB.from_documents(
                        doc_vector_buffer,
                        embedder,
                        uri=db_path,
                        table_name="policy_docs",
                        mode=table_mode,
                    )

                indexed_data[rel_path] = file_hash
                self.stdout.write(self.style.SUCCESS(f"✅ Processed {rel_path}"))

            except TimeoutException:
                self.stderr.write(self.style.WARNING(f"⏳ Skipped (timeout > 60s): {rel_path}"))
                # Cancel alarm if timeout
                signal.alarm(0)
                continue

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error processing {rel_path}: {e}"))

        # Save tracking
        track_path.write_text(json.dumps(indexed_data, indent=2))
        self.stdout.write(self.style.SUCCESS("🚀 Ingestion Complete."))\
        
        # Comment this if you want to see the files
        if os.path.exists(track_path):
            os.remove(track_path)
