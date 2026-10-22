"""Testes do agregador base + trilhas (sopro.core.glossary.aggregate)."""

from pathlib import Path

from sopro.core.glossary.aggregate import aggregate_packages
from sopro.core.glossary.package import DomainPackage, Manifest, Sense, Term
from sopro.core.repo import Database, Repository, import_package


def _package(slug: str, terms, *, parent=None, track=None, order=None, stop=()):
    return DomainPackage(
        manifest=Manifest(
            slug=slug,
            name=slug,
            version="0.1.0",
            source_lang="en",
            output_langs=("pt-BR",),
            license="MIT",
            authors=("Lucas",),
            created_at="2026-10-21",
            parent_slug=parent,
            track=track,
            track_label=track,
            track_order=order,
        ),
        terms=tuple(terms),
        stoplist=tuple(stop),
        path=Path("."),
    )


def _term(name, senses, *, tracks=(), priority=3):
    return Term(
        canonical_en=name,
        pos="noun",
        priority=priority,
        tracks=tuple(tracks),
        senses=tuple(senses),
    )


def _sense(translation, *, ordinal=1, track=None, definition=None):
    return Sense(
        ordinal=ordinal,
        domain_tag="tech",
        translation_pt=translation,
        definition_pt=definition or f"Definição de {translation}.",
        track=track,
    )


def test_aggregate_merges_shared_term_with_unique_ordinals_and_tracks():
    base = _package(
        "tech-en-pt",
        [_term("cache", [_sense("cache genérico")], tracks=("backend", "frontend"))],
        stop=("common",),
    )
    backend = _package(
        "tech-backend-en-pt",
        [_term("cache", [_sense("cache de servidor", track="backend")], tracks=("backend",))],
        parent="tech-en-pt",
        track="backend",
        order=5,
        stop=("server",),
    )
    frontend = _package(
        "tech-frontend-en-pt",
        [_term("cache", [_sense("cache de navegador", track="frontend")], tracks=("frontend",))],
        parent="tech-en-pt",
        track="frontend",
        order=4,
        stop=("browser",),
    )

    aggregate = aggregate_packages(base, [frontend, backend], ("backend",))

    assert len(aggregate.terms) == 1
    term = aggregate.terms[0]
    assert [s.ordinal for s in term.senses] == [1, 2]
    assert term.senses[0].translation_pt == "cache de servidor"
    assert term.senses[1].translation_pt == "cache genérico"
    assert set(term.tracks) == {"backend", "frontend"}
    assert aggregate.stoplist == ("common", "server")


def test_aggregate_empty_active_tracks_means_all():
    base = _package("tech-en-pt", [_term("api", [_sense("API")])])
    backend = _package(
        "tech-backend-en-pt",
        [_term("queue", [_sense("fila", track="backend")])],
        parent="tech-en-pt",
        track="backend",
        order=5,
    )
    frontend = _package(
        "tech-frontend-en-pt",
        [_term("dom", [_sense("DOM", track="frontend")])],
        parent="tech-en-pt",
        track="frontend",
        order=4,
    )

    aggregate = aggregate_packages(base, [backend, frontend])

    assert {t.canonical_en for t in aggregate.terms} == {"api", "queue", "dom"}


def test_aggregate_merges_aliases_and_hints():
    base = _package(
        "tech-en-pt",
        [
            Term(
                canonical_en="model",
                pos="noun",
                aliases=("ML model",),
                context_hints=("treino",),
                senses=(_sense("modelo"),),
            )
        ],
    )
    data = _package(
        "tech-data-science-en-pt",
        [
            Term(
                canonical_en="model",
                pos="noun",
                aliases=("estimator", "ML model"),
                context_hints=("dataset", "treino"),
                senses=(_sense("estimador", track="data-science"),),
                tracks=("data-science",),
            )
        ],
        parent="tech-en-pt",
        track="data-science",
        order=2,
    )

    aggregate = aggregate_packages(base, [data], ("data-science",))
    term = aggregate.terms[0]

    assert term.aliases == ("ML model", "estimator")
    assert term.context_hints == ("treino", "dataset")
    assert term.tracks == ("data-science",)


def test_build_aggregate_from_repo_uses_parent_slug(tmp_path):
    seed = Path("data/domains/tech-en-pt")
    track_dir = tmp_path / "tech-backend-en-pt"
    track_dir.mkdir()
    (track_dir / "manifest.json").write_text(
        """{
  "slug": "tech-backend-en-pt", "name": "Backend", "version": "0.1.0",
  "source_lang": "en", "output_langs": ["pt-BR"], "license": "MIT",
  "authors": ["Lucas"], "created_at": "2026-10-21",
  "parent_slug": "tech-en-pt", "track": "backend", "track_label": "Backend",
  "track_order": 5
}""",
        encoding="utf-8",
    )
    (track_dir / "terms.json").write_text(
        """[{
  "canonical_en": "queue", "pos": "noun", "tracks": ["backend"],
  "senses": [{"ordinal": 1, "domain_tag": "tech", "translation_pt": "fila",
              "definition_pt": "Estrutura de espera.", "track": "backend"}]
}]""",
        encoding="utf-8",
    )

    repo = Repository(Database(":memory:"))
    import_package(repo, seed)
    import_package(repo, track_dir)

    from sopro.core.glossary.aggregate import build_aggregate_from_repo

    aggregate = build_aggregate_from_repo(repo, "tech-en-pt", ("backend",))

    assert any(term.canonical_en == "queue" for term in aggregate.terms)
    assert aggregate.manifest.slug == "tech-en-pt"
