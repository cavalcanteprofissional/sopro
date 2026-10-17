"""Conexão e aplicação de migrações do SQLite (docs/02 §6, docs/05 A6)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sopro.core.repo.migrations import MIGRATIONS

DEFAULT_DB_FILENAME = "sopro.db"


class Database:
    """Envolve uma conexão SQLite e mantém o esquema migrado."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn: sqlite3.Connection | None = None

    @property
    def path(self) -> str:
        return self._path

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        return self._conn

    @property
    def connection(self) -> sqlite3.Connection:
        return self.connect()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        except Exception:
            raise

    def schema_version(self) -> int:
        row = self.connect().execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row is not None else 0

    def migrate(self) -> int:
        """Aplica as migrações pendentes e devolve a versão resultante."""
        connection = self.connect()
        current = self.schema_version()
        for version, script in MIGRATIONS:
            if version > current:
                connection.executescript(script)
                connection.execute(f"PRAGMA user_version = {int(version)}")
                connection.commit()
                current = version
        return current
