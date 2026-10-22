"""Testes de carga de pacotes de domínio (sopro.core.glossary.package)."""

import json
from pathlib import Path

import pytest

from sopro.core.glossary.package import (
    DomainPackage,
    Manifest,
    PackageError,
    Term,
    list_package_slugs,
    load_package,
)

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "data" / "domains" / "tech-en-pt"


def make_term(**overrides) -> Term:
    data = {
        "canonical_en": "term",
        "pos": "noun",
        "aliases": [],
        "priority": 1,
        "is_ambiguous": False,
        "stoplisted": False,
        "context_hints": [],
        "senses": [
            {
                "ordinal": 1,
                "domain_tag": "tech",
                "translation_pt": "tradução",
                "definition_pt": "definição curta.",
            }
        ],
        "source": "curado",
        "needs_review": True,
    }
    data.update(overrides)
    return Term.from_dict(data)


def make_package(terms, stoplist=(), slug="tech-en-pt", **manifest_overrides) -> DomainPackage:
    manifest_data = {
        "slug": slug,
        "name": "Teste",
        "version": "0.1.0",
        "source_lang": "en",
        "output_langs": ["pt-BR"],
        "license": "MIT",
        "authors": ["teste"],
        "created_at": "2026-10-07",
    }
    manifest_data.update(manifest_overrides)
    return DomainPackage(
        manifest=Manifest.from_dict(manifest_data),
        terms=tuple(terms),
        stoplist=tuple(stoplist),
        path=Path("."),
    )


def test_load_real_seed_package():
    package = load_package(PACKAGE_DIR)

    assert package.manifest.slug == "tech-en-pt"
    assert package.manifest.version == "0.2.0"
    assert package.domain_tag == "tech"
    assert len(package.terms) >= 50
    assert "model" in package.stoplist


def test_load_missing_directory_raises():
    with pytest.raises(PackageError):
        load_package(PACKAGE_DIR / "nao-existe")


def test_load_invalid_json_raises(tmp_path):
    (tmp_path / "manifest.json").write_text("{ inválido", encoding="utf-8")
    (tmp_path / "terms.json").write_text("[]", encoding="utf-8")

    with pytest.raises(PackageError):
        load_package(tmp_path)


def test_domain_senses_filters_by_tag():
    t = make_term(
        senses=[
            {"ordinal": 1, "domain_tag": "tech", "translation_pt": "a", "definition_pt": "a"},
            {"ordinal": 2, "domain_tag": "general", "translation_pt": "b", "definition_pt": "b"},
        ]
    )
    assert [s.ordinal for s in t.domain_senses("tech")] == [1]
    assert [s.ordinal for s in t.domain_senses("general")] == [2]


def test_list_package_slugs_reads_manifest(tmp_path):
    pkg = tmp_path / "custom-dir"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({"slug": "law-en-pt"}), encoding="utf-8"
    )
    (pkg / "terms.json").write_text("[]", encoding="utf-8")

    assert list_package_slugs(tmp_path) == ("law-en-pt",)


def test_list_package_slugs_skips_folders_without_manifest(tmp_path):
    (tmp_path / "empty").mkdir()
    (tmp_path / "loose.txt").write_text("x", encoding="utf-8")

    assert list_package_slugs(tmp_path) == ()


def test_list_package_slugs_missing_root_returns_empty(tmp_path):
    assert list_package_slugs(tmp_path / "nao-existe") == ()


def test_manifest_domain_tag_from_slug():
    manifest = Manifest.from_dict(
        {
            "slug": "saude-en-pt",
            "name": "Saúde",
            "version": "0.1.0",
            "source_lang": "en",
            "output_langs": ["pt-BR"],
            "license": "MIT",
            "authors": ["x"],
            "created_at": "2026-10-07",
        }
    )
    assert manifest.domain_tag == "saude"
