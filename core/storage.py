import json
import sqlite3
from typing import Optional

from core import config


def _connect():
    config.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(config.SQLITE_PATH)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_path TEXT,
                stored_path TEXT,
                state TEXT,
                application_number TEXT,
                program_title TEXT,
                application_type TEXT,
                approved_effective_date TEXT,
                year INTEGER,
                extra_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                page INTEGER,
                order_index INTEGER,
                text TEXT
            )
            """
        )


def clear_all() -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chunks")
        conn.execute("DELETE FROM documents")


def insert_document(
    source_path: str,
    stored_path: str,
    state: str,
    application_number: str,
    program_title: str,
    application_type: str,
    approved_effective_date: Optional[str],
    year: Optional[int],
    extra: dict,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (
                source_path, stored_path, state, application_number,
                program_title, application_type, approved_effective_date,
                year, extra_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source_path,
                stored_path,
                state,
                application_number,
                program_title,
                application_type,
                approved_effective_date,
                year,
                json.dumps(extra or {}),
            ),
        )
        return int(cursor.lastrowid)


def insert_chunk(document_id: int, text: str, page: int, order_index: int) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chunks (document_id, page, order_index, text)
            VALUES (?, ?, ?, ?)
            """,
            (document_id, page, order_index, text),
        )
        return int(cursor.lastrowid)
