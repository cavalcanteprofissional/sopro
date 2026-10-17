"""Testes do banco e das migrações (sopro.core.repo.database)."""

import sqlite3

from sopro.core.repo.database import Database
from sopro.core.repo.migrations import LATEST_VERSION

_EXPECTED_TABLES = {
    "domain",
    "term",
    "term_alias",
    "sense",
    "term_i18n",
    "term_fts",
    "session",
    "detection",
    "generated_entry",
    "setting",
}


def test_migrate_sets_latest_version():
    db = Database(":memory:")

    version = db.migrate()

    assert version == LATEST_VERSION
    assert db.schema_version() == LATEST_VERSION


def test_migrate_is_idempotent():
    db = Database(":memory:")

    first = db.migrate()
    second = db.migrate()

    assert first == second == LATEST_VERSION


def test_all_tables_created():
    db = Database(":memory:")
    db.migrate()

    rows = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    ).fetchall()
    names = {row["name"] for row in rows}

    assert _EXPECTED_TABLES <= names


def test_foreign_keys_enabled():
    db = Database(":memory:")
    db.migrate()

    enabled = db.connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1


def test_file_database_persists(tmp_path):
    path = tmp_path / "sopro.db"
    with Database(path) as db:
        db.migrate()

    with Database(path) as reopened:
        assert reopened.schema_version() == LATEST_VERSION


def test_foreign_key_violation_is_enforced():
    db = Database(":memory:")
    db.migrate()

    try:
        db.connection.execute(
            "INSERT INTO term(domain_id, canonical_en) VALUES(999, 'x')"
        )
    except sqlite3.IntegrityError:
        pass
    else:  # pragma: no cover
        raise AssertionError("esperava IntegrityError por chave estrangeira")
