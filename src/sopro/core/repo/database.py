"""Conexão e aplicação de migrações do SQLite (docs/02 §6, docs/05 A6).

Bancos em arquivo usam **uma conexão por thread** (``threading.local``): o
pipeline de áudio grava detecções enquanto a UI lê o histórico, sem violar a
restrição do ``sqlite3`` de que a conexão só pode ser usada na thread que a criou.
WAL e ``busy_timeout`` permitem leitura e escrita concorrentes no mesmo arquivo.

Bancos ``:memory:`` (testes e uso efêmero) compartilham uma única conexão com
``check_same_thread=False``, serializada por um ``RLock``.
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sopro.core.repo.migrations import MIGRATIONS

DEFAULT_DB_FILENAME = "sopro.db"


class Database:
    """Envolve conexões SQLite (uma por thread) e mantém o esquema migrado."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._is_memory = self._path == ":memory:"
        self._local = threading.local()
        self._shared: sqlite3.Connection | None = None
        self._lock = threading.RLock()
        self._migrate_lock = threading.Lock()

    @property
    def path(self) -> str:
        return self._path

    def _new_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._path,
            timeout=5.0,
            check_same_thread=self._is_memory,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if not self._is_memory:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def connect(self) -> sqlite3.Connection:
        """Devolve a conexão da thread atual (criando-a sob demanda)."""
        if self._is_memory:
            with self._lock:
                if self._shared is None:
                    self._shared = self._new_connection()
                return self._shared
        connection = getattr(self._local, "connection", None)
        if connection is None:
            connection = self._new_connection()
            self._local.connection = connection
        return connection

    @property
    def connection(self) -> sqlite3.Connection:
        return self.connect()

    def close(self) -> None:
        """Fecha a conexão da thread atual (ou a compartilhada, em memória)."""
        if self._is_memory:
            with self._lock:
                if self._shared is not None:
                    self._shared.close()
                    self._shared = None
            return
        connection = getattr(self._local, "connection", None)
        if connection is not None:
            connection.close()
            self._local.connection = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self._is_memory:
            with self._lock:
                connection = self.connect()
                with connection:
                    yield connection
        else:
            connection = self.connect()
            with connection:
                yield connection

    def _read_schema_version(self, connection: sqlite3.Connection) -> int:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row is not None else 0

    def schema_version(self) -> int:
        if self._is_memory:
            with self._lock:
                return self._read_schema_version(self.connect())
        return self._read_schema_version(self.connect())

    def migrate(self) -> int:
        """Aplica as migrações pendentes e devolve a versão resultante."""
        with self._migrate_lock:
            connection = self.connect()
            current = self._read_schema_version(connection)
            for version, script in MIGRATIONS:
                if version > current:
                    connection.executescript(script)
                    connection.execute(f"PRAGMA user_version = {int(version)}")
                    connection.commit()
                    current = version
            return current
