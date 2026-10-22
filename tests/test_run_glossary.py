"""Testes do carregamento de base + trilhas no app (sem Qt)."""

from pathlib import Path

from sopro.app.run import _load_active_glossary
from sopro.core.config import Settings
from sopro.core.repo import Database, Repository


def _write_package(path: Path, manifest: dict, terms: list[dict]) -> None:
    import json

    path.mkdir()
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (path / "terms.json").write_text(json.dumps(terms), encoding="utf-8")


def _base_manifest(slug: str) -> dict:
    return {
        "slug": slug,
        "name": "Base",
        "version": "0.1.0",
        "source_lang": "en",
        "output_langs": ["pt-BR"],
        "license": "MIT",
        "authors": ["Lucas"],
        "created_at": "2026-10-21",
        "track_order": 0,
    }


def _track_manifest(slug: str, track: str, order: int) -> dict:
    manifest = _base_manifest(slug)
    manifest.update(
        {
            "name": track,
            "parent_slug": "tech-en-pt",
            "track": track,
            "track_label": track,
            "track_order": order,
        }
    )
    return manifest


def test_loads_base_and_active_track(tmp_path):
    _write_package(
        tmp_path / "tech-en-pt",
        _base_manifest("tech-en-pt"),
        [{"canonical_en": "api", "pos": "noun", "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "API", "definition_pt": "Interface."}]}],
    )
    _write_package(
        tmp_path / "tech-backend-en-pt",
        _track_manifest("tech-backend-en-pt", "backend", 5),
        [{"canonical_en": "queue", "pos": "noun", "tracks": ["backend"], "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "fila", "definition_pt": "Espera.", "track": "backend"}]}],
    )
    _write_package(
        tmp_path / "tech-frontend-en-pt",
        _track_manifest("tech-frontend-en-pt", "frontend", 4),
        [{"canonical_en": "dom", "pos": "noun", "tracks": ["frontend"], "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "DOM", "definition_pt": "Árvore.", "track": "frontend"}]}],
    )

    repo = Repository(Database(":memory:"))
    settings = Settings(active_domains=("tech-en-pt",), active_tracks=("backend",))

    loaded = _load_active_glossary(repo, settings, tmp_path)

    names = {term.canonical_en for term in loaded.package.terms}
    assert names == {"api", "queue"}
    assert len(loaded.domain_ids) == 2
    assert loaded.active_tracks == ("backend",)


def test_configured_track_slug_derives_active_track(tmp_path):
    _write_package(
        tmp_path / "tech-en-pt",
        _base_manifest("tech-en-pt"),
        [{"canonical_en": "api", "pos": "noun", "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "API", "definition_pt": "Interface."}]}],
    )
    _write_package(
        tmp_path / "tech-backend-en-pt",
        _track_manifest("tech-backend-en-pt", "backend", 5),
        [{"canonical_en": "queue", "pos": "noun", "tracks": ["backend"], "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "fila", "definition_pt": "Espera.", "track": "backend"}]}],
    )
    _write_package(
        tmp_path / "tech-frontend-en-pt",
        _track_manifest("tech-frontend-en-pt", "frontend", 4),
        [{"canonical_en": "dom", "pos": "noun", "tracks": ["frontend"], "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "DOM", "definition_pt": "Árvore.", "track": "frontend"}]}],
    )

    repo = Repository(Database(":memory:"))
    settings = Settings(active_domains=("tech-backend-en-pt",))

    loaded = _load_active_glossary(repo, settings, tmp_path)

    names = {term.canonical_en for term in loaded.package.terms}
    assert names == {"api", "queue"}
    assert loaded.active_tracks == ("backend",)
