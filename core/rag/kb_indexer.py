"""Knowledge-base indexer: embed coded segments into LanceDB.

Manages a separate LanceDB table ('coded_segments') from the main policy-doc
store. The table powers few-shot retrieval for the RAG coder.
"""
import json
from pathlib import Path
from typing import Callable

import lancedb as _lancedb
from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document

from core import config


def _make_embedder(provider: str):
    if provider.upper() == "OPENAI":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model=config.OPENAI_EMBEDDING_MODEL)
    from langchain_ollama import OllamaEmbeddings
    return OllamaEmbeddings(model=config.OLLAMA_EMBEDDING_MODEL)


def load_segments(path: str | Path) -> list[dict]:
    """Load coded segments from a JSONL file (one JSON object per line)."""
    segments = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                segments.append(json.loads(line))
    return segments


def index_status() -> dict:
    """Return {'exists': bool, 'row_count': int} for the coded_segments table."""
    db = _lancedb.connect(str(config.LANCE_DB_PATH))
    if "coded_segments" not in db.table_names():
        return {"exists": False, "row_count": 0}
    return {"exists": True, "row_count": db.open_table("coded_segments").count_rows()}


def drop_index() -> None:
    """Drop the coded_segments table so it can be rebuilt from scratch."""
    db = _lancedb.connect(str(config.LANCE_DB_PATH))
    if "coded_segments" in db.table_names():
        db.drop_table("coded_segments")


def build_index(
    segments: list[dict],
    provider: str = "OLLAMA",
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    """Embed all segments and store them in LanceDB. Returns segments indexed."""
    valid = [s for s in segments if s.get("text", "").strip()]
    embedder = _make_embedder(provider)

    docs = [
        Document(
            page_content=seg["text"],
            metadata={
                "document": seg.get("document", ""),
                "code": seg.get("code", ""),
                "code_path": seg.get("code_path", ""),
                "coder": seg.get("coder", ""),
                "start": int(seg.get("start", 0)),
                "end": int(seg.get("end", 0)),
            },
        )
        for seg in valid
    ]

    store = LanceDB(
        embedding=embedder,
        uri=str(config.LANCE_DB_PATH),
        table_name="coded_segments",
    )

    # Add in batches of 100 so the progress callback fires regularly
    batch_size = 100
    for i in range(0, len(docs), batch_size):
        store.add_documents(docs[i : i + batch_size])
        if progress_callback:
            progress_callback(min(i + batch_size, len(docs)), len(docs))

    return len(docs)


def get_store(provider: str = "OLLAMA") -> LanceDB:
    """Return the LanceDB vector store for the coded_segments table."""
    return LanceDB(
        embedding=_make_embedder(provider),
        uri=str(config.LANCE_DB_PATH),
        table_name="coded_segments",
    )


def retrieve_examples(query: str, store: LanceDB, k: int = 5) -> list[dict]:
    """Return k-nearest coded examples for a query span."""
    results = store.similarity_search_with_score(query, k=k)
    return [
        {
            "text": doc.page_content,
            "code": doc.metadata.get("code", ""),
            "code_path": doc.metadata.get("code_path", ""),
            "document": doc.metadata.get("document", ""),
            "coder": doc.metadata.get("coder", ""),
            "score": float(score),
        }
        for doc, score in results
    ]
