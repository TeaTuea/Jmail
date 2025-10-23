from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Generator


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._initialize()

    def _initialize(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            conn = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_user(self, *, email: str, password_hash: str, display_name: str | None) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, display_name) VALUES (?, ?, ?)",
                (email, password_hash, display_name),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_user_by_email(self, email: str) -> sqlite3.Row | None:
        with self.connect() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            return cursor.fetchone()

    def get_user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cursor.fetchone()


__all__ = ["Database"]
