"""Carregamento de pacotes de domínio no formato de docs/07.

Um pacote de domínio é um diretório contendo:

- ``manifest.json`` — metadados do pacote;
- ``terms.json`` — lista de termos (uma entrada por termo, com suas acepções);
- ``stoplist.txt`` — palavras comuns que só disparam com contexto de domínio.

O carregamento é tolerante a campos ausentes (aplica padrões), mas estruturado:
os objetos resultantes são imutáveis e prontos para consumo pelo núcleo.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

MANIFEST_FILENAME = "manifest.json"
TERMS_FILENAME = "terms.json"
STOPLIST_FILENAME = "stoplist.txt"

VALID_POS = ("noun", "verb", "adjective", "acronym", "phrase")

DEFAULT_DOMAIN_TAG = "general"


class PackageError(Exception):
    """Erro ao ler ou interpretar um pacote de domínio."""


@dataclass(frozen=True)
class Sense:
    """Uma acepção (sentido) de um termo."""

    ordinal: int
    domain_tag: str
    translation_pt: str
    definition_pt: str
    register: str | None = None
    example_en: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "Sense":
        return cls(
            ordinal=int(data["ordinal"]),
            domain_tag=str(data.get("domain_tag", DEFAULT_DOMAIN_TAG)),
            translation_pt=str(data.get("translation_pt", "")),
            definition_pt=str(data.get("definition_pt", "")),
            register=data.get("register"),
            example_en=data.get("example_en"),
        )


@dataclass(frozen=True)
class Term:
    """Um termo do glossário, com forma canônica e acepções."""

    canonical_en: str
    pos: str
    aliases: tuple[str, ...] = ()
    priority: int = 3
    is_ambiguous: bool = False
    stoplisted: bool = False
    context_hints: tuple[str, ...] = ()
    senses: tuple[Sense, ...] = ()
    source: str = "curado"
    needs_review: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Term":
        return cls(
            canonical_en=str(data["canonical_en"]),
            pos=str(data.get("pos", "")),
            aliases=tuple(str(a) for a in (data.get("aliases") or ())),
            priority=int(data.get("priority", 3)),
            is_ambiguous=bool(data.get("is_ambiguous", False)),
            stoplisted=bool(data.get("stoplisted", False)),
            context_hints=tuple(str(h) for h in (data.get("context_hints") or ())),
            senses=tuple(Sense.from_dict(s) for s in (data.get("senses") or ())),
            source=str(data.get("source", "curado")),
            needs_review=bool(data.get("needs_review", True)),
        )

    def domain_senses(self, domain_tag: str) -> tuple[Sense, ...]:
        """Acepções marcadas com a etiqueta do domínio ativo."""
        return tuple(s for s in self.senses if s.domain_tag == domain_tag)


@dataclass(frozen=True)
class Manifest:
    """Manifesto do pacote de domínio (docs/07 §1)."""

    slug: str
    name: str
    version: str
    source_lang: str
    output_langs: tuple[str, ...]
    license: str
    authors: tuple[str, ...]
    created_at: str
    embedding_model: str | None = None

    @property
    def domain_tag(self) -> str:
        """Etiqueta de domínio derivada do slug (ex.: ``tech-en-pt`` → ``tech``)."""
        return self.slug.split("-", 1)[0]

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        return cls(
            slug=str(data.get("slug", "")),
            name=str(data.get("name", "")),
            version=str(data.get("version", "")),
            source_lang=str(data.get("source_lang", "")),
            output_langs=tuple(str(x) for x in (data.get("output_langs") or ())),
            license=str(data.get("license", "")),
            authors=tuple(str(x) for x in (data.get("authors") or ())),
            created_at=str(data.get("created_at", "")),
            embedding_model=data.get("embedding_model"),
        )


@dataclass(frozen=True)
class DomainPackage:
    """Um pacote de domínio carregado do disco."""

    manifest: Manifest
    terms: tuple[Term, ...]
    stoplist: tuple[str, ...]
    path: Path

    @property
    def domain_tag(self) -> str:
        return self.manifest.domain_tag


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PackageError(f"arquivo não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PackageError(f"JSON inválido em {path}: {exc}") from exc


def _read_stoplist(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    words = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        words.append(line.lower())
    return tuple(words)


def load_package(path: str | Path) -> DomainPackage:
    """Carrega um pacote de domínio de um diretório."""
    base = Path(path)
    if not base.is_dir():
        raise PackageError(f"diretório do pacote não encontrado: {base}")

    manifest_data = _read_json(base / MANIFEST_FILENAME)
    if not isinstance(manifest_data, dict):
        raise PackageError(f"{MANIFEST_FILENAME} deve conter um objeto JSON")

    terms_data = _read_json(base / TERMS_FILENAME)
    if not isinstance(terms_data, list):
        raise PackageError(f"{TERMS_FILENAME} deve conter uma lista JSON")

    try:
        manifest = Manifest.from_dict(manifest_data)
        terms = tuple(Term.from_dict(t) for t in terms_data)
    except (KeyError, TypeError, ValueError) as exc:
        raise PackageError(f"estrutura de termo inválida: {exc}") from exc

    return DomainPackage(
        manifest=manifest,
        terms=terms,
        stoplist=_read_stoplist(base / STOPLIST_FILENAME),
        path=base,
    )
