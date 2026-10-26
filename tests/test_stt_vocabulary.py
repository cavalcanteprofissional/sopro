"""Testes da dica de vocabulário do STT (sopro.core.stt.vocabulary)."""

from sopro.core.stt.vocabulary import vocabulary_hint
from tests.test_glossary_package import make_package, make_term


def test_hint_includes_spoken_acronym_aliases():
    package = make_package(
        [
            make_term(
                canonical_en="API",
                pos="acronym",
                aliases=["ai pi ai", "a p i"],
                priority=1,
            )
        ]
    )

    hint = vocabulary_hint(package)

    assert "API" in hint
    assert "ai pi ai" in hint
    assert "a p i" in hint


def test_hint_prioritizes_terms_from_active_tracks():
    package = make_package(
        [
            make_term(canonical_en="base", priority=1, tracks=[]),
            make_term(canonical_en="backend", priority=3, tracks=["backend"]),
            make_term(canonical_en="frontend", priority=2, tracks=["frontend"]),
        ]
    )

    hint = vocabulary_hint(package, active_tracks=("backend",))

    assert hint[0] == "backend"
    assert "frontend" in hint


def test_hint_respects_token_limit_and_deduplicates():
    package = make_package(
        [
            make_term(canonical_en="alpha", aliases=["Alpha"], priority=1),
            make_term(canonical_en="beta", priority=2),
        ]
    )

    hint = vocabulary_hint(package, limit=6)

    assert len(hint) == 2
    assert hint.count("alpha") == 1
    assert vocabulary_hint(package, limit=0) == ()
