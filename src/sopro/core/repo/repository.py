"""Repositório de dados (SQLite): domínios, termos, sessões, detecções e histórico.

Implementa o modelo de docs/02 §6. O esquema é migrado na construção; todas as
escritas são idempotentes o quanto possível para permitir reimportação de pacotes.
`context_snippet` é opcional e nunca é exposto na leitura por padrão (privacidade).
"""

from __future__ import annotations

import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from sopro.core.repo.database import Database
from sopro.core.repo.export import history_to_csv, history_to_markdown
from sopro.core.repo.models import (
    DetectionRecord,
    DomainRecord,
    GeneratedEntryRecord,
    HistoryEntry,
    SenseInput,
    SenseRecord,
    SessionRecord,
    TermRecord,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _split_sources(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(part for part in value.split(",") if part)


class Repository:
    """Acesso tipado ao banco local do Sopro."""

    def __init__(self, database: Database) -> None:
        self._db = database
        self._db.migrate()

    @property
    def database(self) -> Database:
        return self._db

    # -- domínios ------------------------------------------------------------
    def upsert_domain(
        self,
        slug: str,
        name: str = "",
        version: str = "",
        license: str = "",
        active: bool = True,
    ) -> int:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO domain(slug, name, version, license, active) "
                "VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(slug) DO UPDATE SET "
                "name=excluded.name, version=excluded.version, "
                "license=excluded.license, active=excluded.active",
                (slug, name, version, license, int(active)),
            )
            row = conn.execute("SELECT id FROM domain WHERE slug = ?", (slug,)).fetchone()
        return int(row["id"])

    def get_domain(self, slug: str) -> DomainRecord | None:
        row = self._db.connection.execute(
            "SELECT * FROM domain WHERE slug = ?", (slug,)
        ).fetchone()
        return _domain(row) if row else None

    def list_domains(self) -> list[DomainRecord]:
        rows = self._db.connection.execute(
            "SELECT * FROM domain ORDER BY slug"
        ).fetchall()
        return [_domain(row) for row in rows]

    def set_stoplist(self, domain_id: int, words: Sequence[str]) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM domain_stoplist WHERE domain_id = ?", (domain_id,))
            for word in words:
                normalized = word.strip().lower()
                if normalized:
                    conn.execute(
                        "INSERT OR IGNORE INTO domain_stoplist(domain_id, word) "
                        "VALUES(?, ?)",
                        (domain_id, normalized),
                    )

    def get_stoplist(self, domain_id: int) -> tuple[str, ...]:
        rows = self._db.connection.execute(
            "SELECT word FROM domain_stoplist WHERE domain_id = ? ORDER BY word",
            (domain_id,),
        ).fetchall()
        return tuple(row["word"] for row in rows)

    # -- termos, aliases e acepções -----------------------------------------
    def add_term(
        self,
        domain_id: int,
        canonical_en: str,
        pos: str = "",
        priority: int = 3,
        is_ambiguous: bool = False,
        stoplisted: bool = False,
        aliases: Sequence[str] = (),
        senses: Sequence[SenseInput] = (),
    ) -> int:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO term(domain_id, canonical_en, pos, priority, is_ambiguous, stoplisted) "
                "VALUES(?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(domain_id, canonical_en) DO UPDATE SET "
                "pos=excluded.pos, priority=excluded.priority, "
                "is_ambiguous=excluded.is_ambiguous, stoplisted=excluded.stoplisted",
                (domain_id, canonical_en, pos, priority, int(is_ambiguous), int(stoplisted)),
            )
            row = conn.execute(
                "SELECT id FROM term WHERE domain_id = ? AND canonical_en = ?",
                (domain_id, canonical_en),
            ).fetchone()
            term_id = int(row["id"])

            conn.execute("DELETE FROM term_alias WHERE term_id = ?", (term_id,))
            for alias in aliases:
                conn.execute(
                    "INSERT OR IGNORE INTO term_alias(term_id, alias, kind) VALUES(?, ?, '')",
                    (term_id, alias),
                )

            conn.execute("DELETE FROM sense WHERE term_id = ?", (term_id,))
            for sense in senses:
                conn.execute(
                    "INSERT INTO sense(term_id, ordinal, domain_tag, translation_pt, "
                    "definition_pt, register, example_en) VALUES(?, ?, ?, ?, ?, ?, ?)",
                    (
                        term_id,
                        sense.ordinal,
                        sense.domain_tag,
                        sense.translation_pt,
                        sense.definition_pt,
                        sense.register,
                        sense.example_en,
                    ),
                )

            conn.execute("DELETE FROM term_fts WHERE rowid = ?", (term_id,))
            conn.execute(
                "INSERT INTO term_fts(rowid, canonical_en, aliases, term_id, domain_id) "
                "VALUES(?, ?, ?, ?, ?)",
                (term_id, canonical_en, " ".join(aliases), term_id, domain_id),
            )
        return term_id

    def get_term(self, term_id: int) -> TermRecord | None:
        row = self._db.connection.execute(
            "SELECT * FROM term WHERE id = ?", (term_id,)
        ).fetchone()
        if row is None:
            return None
        return self._term(row)

    def get_term_by_canonical(
        self, domain_id: int, canonical_en: str
    ) -> TermRecord | None:
        row = self._db.connection.execute(
            "SELECT * FROM term WHERE domain_id = ? AND canonical_en = ?",
            (domain_id, canonical_en),
        ).fetchone()
        return self._term(row) if row else None

    def list_terms(self, domain_id: int | None = None) -> list[TermRecord]:
        if domain_id is None:
            rows = self._db.connection.execute(
                "SELECT * FROM term ORDER BY canonical_en"
            ).fetchall()
        else:
            rows = self._db.connection.execute(
                "SELECT * FROM term WHERE domain_id = ? ORDER BY canonical_en",
                (domain_id,),
            ).fetchall()
        return [self._term(row) for row in rows]

    def list_senses(self, term_id: int) -> list[SenseRecord]:
        rows = self._db.connection.execute(
            "SELECT * FROM sense WHERE term_id = ? ORDER BY ordinal", (term_id,)
        ).fetchall()
        return [
            SenseRecord(
                id=row["id"],
                term_id=row["term_id"],
                ordinal=row["ordinal"],
                domain_tag=row["domain_tag"],
                translation_pt=row["translation_pt"],
                definition_pt=row["definition_pt"],
                register=row["register"],
                example_en=row["example_en"],
            )
            for row in rows
        ]

    def search_terms(self, query: str, limit: int = 20) -> list[TermRecord]:
        """Busca textual (FTS5) sobre termos e aliases."""
        rows = self._db.connection.execute(
            "SELECT term_id FROM term_fts WHERE term_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        results = []
        for row in rows:
            term = self.get_term(int(row["term_id"]))
            if term is not None:
                results.append(term)
        return results

    def _term(self, row) -> TermRecord:
        aliases = self._db.connection.execute(
            "SELECT alias FROM term_alias WHERE term_id = ? ORDER BY alias",
            (row["id"],),
        ).fetchall()
        return TermRecord(
            id=row["id"],
            domain_id=row["domain_id"],
            canonical_en=row["canonical_en"],
            pos=row["pos"],
            priority=row["priority"],
            is_ambiguous=bool(row["is_ambiguous"]),
            stoplisted=bool(row["stoplisted"]),
            aliases=tuple(alias["alias"] for alias in aliases),
        )

    # -- embeddings das acepções (sense_vec) --------------------------------

    def upsert_sense_vector(
        self, sense_id: int, model: str, dim: int, vector: Sequence[float]
    ) -> None:
        """Grava (ou substitui) o embedding de uma acepção."""
        blob = struct.pack(f"<{len(vector)}f", *[float(value) for value in vector])
        with self._db.transaction() as connection:
            connection.execute(
                "INSERT INTO sense_vec (sense_id, model, dim, vector) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(sense_id) DO UPDATE SET "
                "model = excluded.model, dim = excluded.dim, vector = excluded.vector",
                (sense_id, model, dim, blob),
            )

    def get_sense_vector(
        self, sense_id: int, model: str | None = None
    ) -> list[float] | None:
        query = "SELECT dim, vector FROM sense_vec WHERE sense_id = ?"
        params: list[object] = [sense_id]
        if model is not None:
            query += " AND model = ?"
            params.append(model)
        row = self._db.connection.execute(query, params).fetchone()
        if row is None:
            return None
        dim = int(row["dim"])
        return list(struct.unpack(f"<{dim}f", bytes(row["vector"])))

    def list_sense_vectors(
        self, model: str | None = None
    ) -> list[tuple[int, list[float]]]:
        """Todos os embeddings persistidos como ``(sense_id, vetor)``."""
        query = "SELECT sense_id, dim, vector FROM sense_vec"
        params: list[object] = []
        if model is not None:
            query += " WHERE model = ?"
            params.append(model)
        rows = self._db.connection.execute(query, params).fetchall()
        return [
            (
                int(row["sense_id"]),
                list(struct.unpack(f"<{int(row['dim'])}f", bytes(row["vector"]))),
            )
            for row in rows
        ]

    def clear_sense_vectors(self, model: str | None = None) -> int:
        if model is None:
            cursor = self._db.connection.execute("DELETE FROM sense_vec")
        else:
            cursor = self._db.connection.execute(
                "DELETE FROM sense_vec WHERE model = ?", (model,)
            )
        self._db.connection.commit()
        return int(cursor.rowcount or 0)

    # -- sessões -------------------------------------------------------------
    def start_session(
        self,
        title: str = "",
        audio_sources: Sequence[str] = (),
        started_at: str | None = None,
    ) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO session(started_at, ended_at, title, audio_sources) "
                "VALUES(?, NULL, ?, ?)",
                (started_at or _now(), title, ",".join(audio_sources)),
            )
        return int(cursor.lastrowid)

    def end_session(self, session_id: int, ended_at: str | None = None) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE session SET ended_at = ? WHERE id = ?",
                (ended_at or _now(), session_id),
            )

    def get_session(self, session_id: int) -> SessionRecord | None:
        row = self._db.connection.execute(
            "SELECT * FROM session WHERE id = ?", (session_id,)
        ).fetchone()
        return _session(row) if row else None

    def list_sessions(self, limit: int = 50) -> list[SessionRecord]:
        rows = self._db.connection.execute(
            "SELECT * FROM session ORDER BY started_at DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_session(row) for row in rows]

    # -- detecções -----------------------------------------------------------
    def add_detection(
        self,
        session_id: int | None,
        term_id: int | None = None,
        sense_id: int | None = None,
        at: str | None = None,
        source: str = "",
        method: str = "",
        context_snippet: str | None = None,
        learned: bool = False,
    ) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO detection(session_id, term_id, sense_id, at, source, "
                "method, context_snippet, learned) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    term_id,
                    sense_id,
                    at or _now(),
                    source,
                    method,
                    context_snippet,
                    int(learned),
                ),
            )
        return int(cursor.lastrowid)

    def set_detection_learned(self, detection_id: int, learned: bool = True) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE detection SET learned = ? WHERE id = ?",
                (int(learned), detection_id),
            )

    def list_detections(
        self, session_id: int | None = None, limit: int = 100
    ) -> list[DetectionRecord]:
        if session_id is None:
            rows = self._db.connection.execute(
                "SELECT * FROM detection ORDER BY at, id LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._db.connection.execute(
                "SELECT * FROM detection WHERE session_id = ? ORDER BY at, id LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [_detection(row) for row in rows]

    # -- configurações -------------------------------------------------------
    def set_setting(self, key: str, value: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "INSERT INTO setting(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._db.connection.execute(
            "SELECT value FROM setting WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def all_settings(self) -> dict[str, str]:
        rows = self._db.connection.execute("SELECT key, value FROM setting").fetchall()
        return {row["key"]: row["value"] for row in rows}

    def delete_setting(self, key: str) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM setting WHERE key = ?", (key,))

    # -- entradas geradas (fila de aprovação) -------------------------------
    def add_generated_entry(
        self,
        term: str,
        definition: str,
        model: str = "",
        *,
        translation: str = "",
        confidence: float = 0.0,
        approved: bool = False,
    ) -> int:
        """Grava uma entrada gerada por LLM (separada de term/sense até aprovação)."""
        with self._db.transaction() as connection:
            cursor = connection.execute(
                "INSERT INTO generated_entry(term, translation, definition, model, "
                "created_at, confidence, approved) VALUES(?, ?, ?, ?, ?, ?, ?)",
                (
                    term,
                    translation,
                    definition,
                    model,
                    _now(),
                    float(confidence),
                    int(approved),
                ),
            )
            return int(cursor.lastrowid or 0)

    def get_generated_entry(
        self, term: str, model: str | None = None
    ) -> GeneratedEntryRecord | None:
        query = "SELECT * FROM generated_entry WHERE term = ?"
        params: list[object] = [term]
        if model is not None:
            query += " AND model = ?"
            params.append(model)
        query += " ORDER BY id DESC LIMIT 1"
        row = self._db.connection.execute(query, params).fetchone()
        return _generated_entry(row) if row else None

    def list_generated_entries(
        self, approved: bool | None = None
    ) -> list[GeneratedEntryRecord]:
        query = "SELECT * FROM generated_entry"
        params: list[object] = []
        if approved is not None:
            query += " WHERE approved = ?"
            params.append(int(approved))
        query += " ORDER BY created_at DESC, id DESC"
        rows = self._db.connection.execute(query, params).fetchall()
        return [_generated_entry(row) for row in rows]

    def approve_generated_entry(self, entry_id: int) -> None:
        with self._db.transaction() as connection:
            connection.execute(
                "UPDATE generated_entry SET approved = 1 WHERE id = ?", (entry_id,)
            )

    # -- histórico e exportação ---------------------------------------------
    def history(
        self,
        session_id: int | None = None,
        include_context: bool = False,
        limit: int | None = None,
    ) -> list[HistoryEntry]:
        sql = (
            "SELECT d.at AS at, d.session_id AS session_id, "
            "COALESCE(t.canonical_en, '') AS term, "
            "COALESCE(s.translation_pt, '') AS translation, "
            "d.source AS source, d.method AS method, d.learned AS learned, "
            "d.context_snippet AS context_snippet "
            "FROM detection d "
            "LEFT JOIN term t ON t.id = d.term_id "
            "LEFT JOIN sense s ON s.id = d.sense_id"
        )
        params: list[object] = []
        if session_id is not None:
            sql += " WHERE d.session_id = ?"
            params.append(session_id)
        sql += " ORDER BY d.at, d.id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._db.connection.execute(sql, params).fetchall()
        return [
            HistoryEntry(
                at=row["at"],
                session_id=row["session_id"],
                term=row["term"],
                translation=row["translation"],
                source=row["source"],
                method=row["method"],
                learned=bool(row["learned"]),
                context_snippet=row["context_snippet"] if include_context else None,
            )
            for row in rows
        ]

    def export_history_csv(
        self,
        path: str | Path,
        session_id: int | None = None,
        include_context: bool = False,
    ) -> Path:
        entries = self.history(session_id=session_id, include_context=include_context)
        target = Path(path)
        target.write_text(history_to_csv(entries, include_context), encoding="utf-8")
        return target

    def export_history_markdown(
        self,
        path: str | Path,
        session_id: int | None = None,
        include_context: bool = False,
    ) -> Path:
        entries = self.history(session_id=session_id, include_context=include_context)
        target = Path(path)
        target.write_text(
            history_to_markdown(entries, include_context), encoding="utf-8"
        )
        return target


def _domain(row) -> DomainRecord:
    return DomainRecord(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        version=row["version"],
        license=row["license"],
        active=bool(row["active"]),
    )


def _session(row) -> SessionRecord:
    return SessionRecord(
        id=row["id"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        title=row["title"],
        audio_sources=_split_sources(row["audio_sources"]),
    )


def _detection(row) -> DetectionRecord:
    return DetectionRecord(
        id=row["id"],
        session_id=row["session_id"],
        term_id=row["term_id"],
        sense_id=row["sense_id"],
        at=row["at"],
        source=row["source"],
        method=row["method"],
        context_snippet=row["context_snippet"],
        learned=bool(row["learned"]),
    )


def _generated_entry(row) -> GeneratedEntryRecord:
    return GeneratedEntryRecord(
        id=row["id"],
        term=row["term"],
        translation=row["translation"],
        definition=row["definition"],
        model=row["model"],
        created_at=row["created_at"],
        confidence=float(row["confidence"]),
        approved=bool(row["approved"]),
    )
