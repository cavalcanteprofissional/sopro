"""Testes do importador/exportador de pacotes de domínio (sopro.core.repo.importer)."""

import pytest

from sopro.core.glossary.package import load_package
from sopro.core.repo import (
    Database,
    Repository,
    build_domain_package,
    export_package_json,
    import_package,
)

SEED_PATH = "data/domains/tech-en-pt"


def _repo() -> Repository:
    return Repository(Database(":memory:"))


def test_import_seed_package():
    repo = _repo()

    domain_id = import_package(repo, SEED_PATH)

    domain = repo.get_domain("tech-en-pt")
    assert domain.id == domain_id
    assert domain.name  # nome vindo do manifesto
    assert len(repo.list_terms(domain_id)) > 0


def test_imported_terms_have_aliases_and_senses():
    repo = _repo()
    import_package(repo, SEED_PATH)

    term = repo.get_term_by_canonical(repo.get_domain("tech-en-pt").id, "transformer")

    assert term is not None
    assert term.pos == "noun"
    senses = repo.list_senses(term.id)
    assert senses
    assert senses[0].translation_pt


def test_import_makes_terms_searchable_via_fts():
    repo = _repo()
    import_package(repo, SEED_PATH)

    results = repo.search_terms("transformer")

    assert [t.canonical_en for t in results] == ["transformer"]


def test_import_is_idempotent():
    repo = _repo()
    import_package(repo, SEED_PATH)
    before = len(repo.list_terms())

    import_package(repo, SEED_PATH)

    assert len(repo.list_terms()) == before


def test_export_round_trip_matches_source(tmp_path):
    repo = _repo()
    import_package(repo, SEED_PATH)

    out = export_package_json(repo, "tech-en-pt", tmp_path / "tech-out")

    source = load_package(SEED_PATH)
    exported = load_package(out)
    source_terms = {t.canonical_en: t for t in source.terms}
    exported_terms = {t.canonical_en: t for t in exported.terms}
    assert exported_terms.keys() == source_terms.keys()
    assert exported.manifest.slug == source.manifest.slug
    first = next(iter(exported.terms))
    assert first.pos == source_terms[first.canonical_en].pos
    assert sorted(first.aliases) == sorted(source_terms[first.canonical_en].aliases)
    assert sorted(exported.stoplist) == sorted(source.stoplist)
    assert exported.stoplist


def test_export_missing_domain_raises(tmp_path):
    repo = _repo()

    with pytest.raises(ValueError):
        export_package_json(repo, "inexistente", tmp_path / "out")


def test_build_domain_package_rebuilds_terms():
    repo = _repo()
    import_package(repo, SEED_PATH)

    package = build_domain_package(repo, "tech-en-pt")

    source = load_package(SEED_PATH)
    assert {t.canonical_en for t in package.terms} == {t.canonical_en for t in source.terms}
    assert package.manifest.slug == "tech-en-pt"
    assert sorted(package.stoplist) == sorted(source.stoplist)


def test_track_metadata_round_trip(tmp_path):
    import json

    package_dir = tmp_path / "tech-devops-en-pt"
    package_dir.mkdir()
    (package_dir / "manifest.json").write_text(
        json.dumps(
            {
                "slug": "tech-devops-en-pt",
                "name": "Tecnologia — DevOps",
                "version": "0.1.0",
                "source_lang": "en",
                "output_langs": ["pt-BR"],
                "license": "MIT",
                "authors": ["Lucas"],
                "created_at": "2026-10-21",
                "parent_slug": "tech-en-pt",
                "track": "devops",
                "track_label": "DevOps e Nuvem",
                "track_order": 3,
            }
        ),
        encoding="utf-8",
    )
    (package_dir / "terms.json").write_text(
        json.dumps(
            [
                {
                    "canonical_en": "container",
                    "pos": "noun",
                    "tracks": ["devops", "backend"],
                    "senses": [
                        {
                            "ordinal": 1,
                            "domain_tag": "tech",
                            "translation_pt": "contêiner",
                            "definition_pt": "Unidade isolada de software.",
                            "track": "devops",
                        }
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    repo = _repo()
    import_package(repo, package_dir)
    domain = repo.get_domain("tech-devops-en-pt")
    term = repo.get_term_by_canonical(domain.id, "container")
    assert domain.parent_slug == "tech-en-pt"
    assert domain.track == "devops"
    assert domain.track_label == "DevOps e Nuvem"
    assert domain.track_order == 3
    assert term.tracks == ("devops", "backend")

    rebuilt = build_domain_package(repo, "tech-devops-en-pt")
    assert rebuilt.manifest.parent_slug == "tech-en-pt"
    assert rebuilt.manifest.track == "devops"
    assert rebuilt.terms[0].tracks == ("devops", "backend")
    assert rebuilt.terms[0].senses[0].track == "devops"

    out = export_package_json(repo, "tech-devops-en-pt", tmp_path / "out")
    exported = load_package(out)
    assert exported.manifest.parent_slug == "tech-en-pt"
    assert exported.manifest.track_label == "DevOps e Nuvem"
    assert exported.terms[0].tracks == ("devops", "backend")
    assert exported.terms[0].senses[0].track == "devops"
