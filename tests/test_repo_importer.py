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
