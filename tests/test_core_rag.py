"""Testes do núcleo RAG: embeddings, índice, resolvedor, persistência e avaliação."""

import pytest

from sopro.core.glossary.package import Sense, Term, load_package
from sopro.core.rag import (
    HashingEmbedder,
    SenseIndex,
    SenseResolver,
    cosine,
    create_embedder,
    default_embedder,
    embed_domain,
    evaluate,
    load_vectors,
    sense_text,
)
from sopro.core.rag.embeddings import EmbeddingError, tokenize
from sopro.core.repo import Database, Repository, build_domain_package, import_package

SEED_PATH = "data/domains/tech-en-pt"


def _term(*senses: Sense) -> Term:
    return Term(canonical_en="widget", pos="noun", senses=tuple(senses))


def _sense(ordinal: int, tag: str, definition: str, example: str = "") -> Sense:
    return Sense(
        ordinal=ordinal,
        domain_tag=tag,
        translation_pt=f"sentido {ordinal}",
        definition_pt=definition,
        example_en=example or None,
    )


# -- embeddings --------------------------------------------------------------


def test_tokenize_removes_stopwords_and_normalizes():
    assert tokenize("The Model is Large!") == ["model", "large"]


def test_hashing_embedder_is_deterministic_and_normalized():
    embedder = HashingEmbedder(dim=64)
    first = embedder.embed(["a machine learning model"])[0]
    second = embedder.embed(["a machine learning model"])[0]

    assert first == second
    assert len(first) == 64
    assert sum(v * v for v in first) == pytest.approx(1.0)
    assert embedder.name == "hashing-v1-64"


def test_hashing_embedder_similar_texts_score_higher():
    embedder = default_embedder()
    query, near, far = embedder.embed(
        [
            "train the neural model",
            "train the neural network model",
            "boil water for the pasta",
        ]
    )

    assert cosine(query, near) > cosine(query, far)


def test_create_embedder_unknown_raises():
    with pytest.raises(EmbeddingError):
        create_embedder("does-not-exist")


# -- índice vetorial ---------------------------------------------------------


def test_sense_index_returns_nearest_key():
    index = SenseIndex(default_embedder())
    index.build(
        [
            ("ml", "training a neural network model with data"),
            ("cook", "boiling pasta in salty water"),
            ("car", "the electric engine runs quietly"),
        ]
    )

    best = index.search("neural network model training", k=1)

    assert len(index) == 3
    assert best[0].key == "ml"
    assert best[0].score > 0.0


def test_sense_index_empty_returns_nothing():
    index = SenseIndex(default_embedder())
    assert index.search("anything") == []
    assert len(index) == 0


def test_sense_index_add_vector_round_trip():
    index = SenseIndex(default_embedder())
    index.add_vector("only", [1.0, 0.0, 0.0])
    scored = index.search_vector([1.0, 0.0, 0.0], k=1)
    assert scored[0].key == "only"
    assert scored[0].score == pytest.approx(1.0)


# -- resolvedor --------------------------------------------------------------


def test_resolve_single_sense():
    resolver = SenseResolver()
    term = _term(_sense(1, "tech", "only one meaning"))

    resolution = resolver.resolve(term, "any context")

    assert resolution is not None
    assert resolution.method == "single_sense"
    assert resolution.sense.ordinal == 1


def test_resolve_without_senses_returns_none():
    assert SenseResolver().resolve(_term(), "context") is None


def test_resolve_prefers_unique_domain_tag():
    resolver = SenseResolver(domain_tag="tech")
    term = _term(
        _sense(1, "tech", "machine learning context"),
        _sense(2, "general", "everyday context"),
        _sense(3, "general", "another everyday context"),
    )

    resolution = resolver.resolve(term, "unrelated words")

    assert resolution is not None
    assert resolution.method == "domain_tag"
    assert resolution.sense.ordinal == 1


def test_resolve_by_vector_picks_matching_sense():
    resolver = SenseResolver()
    term = _term(
        _sense(1, "general", "equitable treatment of groups", "fairness for all groups"),
        _sense(2, "general", "cracked shell walnut seed", "eat the kernel of the nut"),
    )

    resolution = resolver.resolve(term, "we discuss equitable treatment of groups")

    assert resolution is not None
    assert resolution.method == "vector"
    assert resolution.sense.ordinal == 1


def test_resolve_falls_back_to_llm_below_threshold():
    calls = {"n": 0}

    class Chooser:
        def choose(self, term, context, candidates):
            calls["n"] += 1
            return 1

    resolver = SenseResolver(llm=Chooser(), threshold=1.1)
    term = _term(
        _sense(1, "general", "alpha beta"),
        _sense(2, "general", "gamma delta"),
    )

    resolution = resolver.resolve(term, "completely unrelated")

    assert resolution is not None
    assert resolution.method == "llm"
    assert resolution.sense.ordinal == 2
    assert calls["n"] == 1


def test_resolve_keeps_vector_when_llm_undecided():
    class Chooser:
        def choose(self, term, context, candidates):
            return None

    resolver = SenseResolver(llm=Chooser(), threshold=1.1)
    term = _term(
        _sense(1, "general", "alpha beta"),
        _sense(2, "general", "gamma delta"),
    )

    resolution = resolver.resolve(term, "completely unrelated")

    assert resolution is not None
    assert resolution.method == "vector"


def test_resolve_survives_llm_exception():
    class Chooser:
        def choose(self, term, context, candidates):
            raise RuntimeError("boom")

    resolver = SenseResolver(llm=Chooser(), threshold=1.1)
    term = _term(
        _sense(1, "general", "alpha beta"),
        _sense(2, "general", "gamma delta"),
    )

    resolution = resolver.resolve(term, "completely unrelated")

    assert resolution is not None
    assert resolution.method == "vector"


# -- persistência (sense_vec) ------------------------------------------------


def test_embed_domain_persists_and_loads_vectors():
    repo = Repository(Database(":memory:"))
    domain_id = import_package(repo, SEED_PATH)
    package = build_domain_package(repo, "tech-en-pt")
    embedder = HashingEmbedder(dim=32)

    count = embed_domain(repo, package, domain_id, embedder)
    vectors = load_vectors(repo, package, domain_id, model=embedder.name)

    assert count > 0
    assert len(vectors) == count
    key = next(iter(vectors))
    assert len(vectors[key]) == 32


def test_clear_sense_vectors_removes_all():
    repo = Repository(Database(":memory:"))
    domain_id = import_package(repo, SEED_PATH)
    package = build_domain_package(repo, "tech-en-pt")
    embed_domain(repo, package, domain_id, HashingEmbedder(dim=16))

    removed = repo.clear_sense_vectors()

    assert removed > 0
    assert repo.list_sense_vectors() == []


# -- avaliação de acurácia ---------------------------------------------------


def test_evaluate_ambiguity_accuracy_is_high():
    result = evaluate(SenseResolver())

    assert result.total >= 10
    assert result.accuracy >= 0.85


def test_sense_text_includes_example_and_tag():
    text = sense_text(_sense(1, "tech", "some definition", "an english example"))
    assert "some definition" in text
    assert "an english example" in text
    assert "tech" in text


def test_load_package_domain_tag_is_prefix():
    package = load_package(SEED_PATH)
    assert package.domain_tag == "tech"
