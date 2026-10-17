"""Migrações versionadas do banco SQLite (docs/02 §6, docs/05 A6).

Cada migração é um par ``(versão, SQL)`` aplicado em ordem sobre ``PRAGMA
user_version``. Nunca editar uma migração já publicada: acrescente uma nova.
"""

from __future__ import annotations

SCHEMA_V1 = """
CREATE TABLE domain (
    id       INTEGER PRIMARY KEY,
    slug     TEXT NOT NULL UNIQUE,
    name     TEXT NOT NULL DEFAULT '',
    version  TEXT NOT NULL DEFAULT '',
    license  TEXT NOT NULL DEFAULT '',
    active   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE term (
    id           INTEGER PRIMARY KEY,
    domain_id    INTEGER NOT NULL REFERENCES domain(id) ON DELETE CASCADE,
    canonical_en TEXT NOT NULL,
    pos          TEXT NOT NULL DEFAULT '',
    priority     INTEGER NOT NULL DEFAULT 3,
    is_ambiguous INTEGER NOT NULL DEFAULT 0,
    stoplisted   INTEGER NOT NULL DEFAULT 0,
    UNIQUE (domain_id, canonical_en)
);

CREATE TABLE term_alias (
    term_id INTEGER NOT NULL REFERENCES term(id) ON DELETE CASCADE,
    alias   TEXT NOT NULL,
    kind    TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (term_id, alias)
);

CREATE TABLE sense (
    id             INTEGER PRIMARY KEY,
    term_id        INTEGER NOT NULL REFERENCES term(id) ON DELETE CASCADE,
    ordinal        INTEGER NOT NULL,
    domain_tag     TEXT NOT NULL DEFAULT 'general',
    translation_pt TEXT NOT NULL DEFAULT '',
    definition_pt  TEXT NOT NULL DEFAULT '',
    register       TEXT,
    example_en     TEXT,
    UNIQUE (term_id, ordinal)
);

CREATE TABLE term_i18n (
    sense_id    INTEGER NOT NULL REFERENCES sense(id) ON DELETE CASCADE,
    lang        TEXT NOT NULL,
    translation TEXT NOT NULL DEFAULT '',
    definition  TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (sense_id, lang)
);

CREATE VIRTUAL TABLE term_fts USING fts5 (
    canonical_en,
    aliases,
    term_id UNINDEXED,
    domain_id UNINDEXED,
    tokenize = 'unicode61'
);

CREATE TABLE session (
    id            INTEGER PRIMARY KEY,
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    title         TEXT NOT NULL DEFAULT '',
    audio_sources TEXT NOT NULL DEFAULT ''
);

CREATE TABLE detection (
    id              INTEGER PRIMARY KEY,
    session_id      INTEGER REFERENCES session(id) ON DELETE CASCADE,
    term_id         INTEGER REFERENCES term(id) ON DELETE SET NULL,
    sense_id        INTEGER REFERENCES sense(id) ON DELETE SET NULL,
    at              TEXT NOT NULL,
    source          TEXT NOT NULL DEFAULT '',
    method          TEXT NOT NULL DEFAULT '',
    context_snippet TEXT,
    learned         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_detection_session ON detection(session_id);
CREATE INDEX idx_detection_at ON detection(at);

CREATE TABLE generated_entry (
    id         INTEGER PRIMARY KEY,
    term       TEXT NOT NULL,
    definition TEXT NOT NULL DEFAULT '',
    model      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    approved   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE setting (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SCHEMA_V2 = """
CREATE TABLE domain_stoplist (
    domain_id INTEGER NOT NULL REFERENCES domain(id) ON DELETE CASCADE,
    word      TEXT NOT NULL,
    PRIMARY KEY (domain_id, word)
);
"""

SCHEMA_V3 = """
CREATE TABLE sense_vec (
    sense_id INTEGER PRIMARY KEY REFERENCES sense(id) ON DELETE CASCADE,
    model    TEXT NOT NULL,
    dim      INTEGER NOT NULL,
    vector   BLOB NOT NULL
);
"""

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (1, SCHEMA_V1),
    (2, SCHEMA_V2),
    (3, SCHEMA_V3),
)

LATEST_VERSION = MIGRATIONS[-1][0]
