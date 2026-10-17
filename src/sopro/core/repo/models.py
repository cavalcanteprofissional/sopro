"""Tipos de dados da persistência (docs/02 §6)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DomainRecord:
    id: int
    slug: str
    name: str = ""
    version: str = ""
    license: str = ""
    active: bool = True


@dataclass(frozen=True)
class SenseInput:
    """Acepção a inserir (sem id)."""

    ordinal: int
    domain_tag: str = "general"
    translation_pt: str = ""
    definition_pt: str = ""
    register: str | None = None
    example_en: str | None = None


@dataclass(frozen=True)
class SenseRecord:
    id: int
    term_id: int
    ordinal: int
    domain_tag: str
    translation_pt: str
    definition_pt: str
    register: str | None = None
    example_en: str | None = None


@dataclass(frozen=True)
class TermRecord:
    id: int
    domain_id: int
    canonical_en: str
    pos: str = ""
    priority: int = 3
    is_ambiguous: bool = False
    stoplisted: bool = False
    aliases: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SessionRecord:
    id: int
    started_at: str
    ended_at: str | None = None
    title: str = ""
    audio_sources: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DetectionRecord:
    id: int
    session_id: int | None
    term_id: int | None
    sense_id: int | None
    at: str
    source: str = ""
    method: str = ""
    context_snippet: str | None = None
    learned: bool = False


@dataclass(frozen=True)
class GeneratedEntryRecord:
    """Entrada gerada por LLM, pendente de aprovação (docs/02 §6)."""

    id: int
    term: str
    translation: str = ""
    definition: str = ""
    model: str = ""
    created_at: str = ""
    confidence: float = 0.0
    approved: bool = False


@dataclass(frozen=True)
class HistoryEntry:
    """Linha do histórico (detecção + termo/acepção) para exibição/exportação."""

    at: str
    session_id: int | None
    term: str
    translation: str
    source: str
    method: str
    learned: bool
    context_snippet: str | None = None
