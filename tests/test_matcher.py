"""Testes do casamento de termos (sopro.core.matcher)."""

from pathlib import Path

from sopro.core.glossary.package import load_package
from sopro.core.matcher import Match, Matcher, MatcherConfig, pluralize
from tests.test_glossary_package import make_package, make_term

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "data" / "domains" / "tech-en-pt"


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_pluralize_rules():
    assert pluralize("layer") == "layers"
    assert pluralize("batch") == "batches"
    assert pluralize("city") == "cities"
    assert pluralize("") == ""


def test_matches_multiword_as_single_longest_match():
    package = make_package([make_term(canonical_en="machine learning", priority=1)])
    matcher = Matcher(package)

    matches = matcher.match("Machine learning is fun.")

    assert len(matches) == 1
    assert matches[0].term == "machine learning"
    assert matches[0].surface == "machine learning"


def test_matches_alias_to_canonical_term():
    package = make_package(
        [make_term(canonical_en="gradient descent", aliases=["SGD"], priority=1)]
    )
    matcher = Matcher(package)

    matches = matcher.match("We used SGD here.")

    assert [m.term for m in matches] == ["gradient descent"]
    assert matches[0].surface == "sgd"


def test_generates_plural_variant():
    package = make_package([make_term(canonical_en="embedding", priority=1)])
    matcher = Matcher(package)

    matches = matcher.match("Word embeddings are useful.")

    assert [m.term for m in matches] == ["embedding"]
    assert matches[0].surface == "embeddings"


def test_generates_verb_inflections():
    package = make_package([make_term(canonical_en="deploy", pos="verb", priority=1)])
    matcher = Matcher(package, MatcherConfig(cooldown_s=0))

    matches = matcher.match("We deployed and are deploying again.")

    assert [m.term for m in matches] == ["deploy", "deploy"]
    assert {m.surface for m in matches} == {"deployed", "deploying"}


def test_spoken_acronym_letters_match_canonical_term():
    package = make_package(
        [
            make_term(canonical_en="API", pos="acronym", priority=1),
            make_term(canonical_en="AI", pos="acronym", priority=1),
        ]
    )
    matcher = Matcher(package, MatcherConfig(cooldown_s=0))

    assert [m.term for m in matcher.match("The A P I is ready.")] == ["API"]
    assert [m.term for m in matcher.match("The A.I. model is ready.")] == ["AI"]
    assert [m.term for m in matcher.match("The a-p-i is ready.")] == ["API"]


def test_spoken_acronym_does_not_confuse_ai_and_api():
    package = make_package(
        [
            make_term(canonical_en="API", pos="acronym", priority=1),
            make_term(canonical_en="AI", pos="acronym", priority=1),
        ]
    )
    matcher = Matcher(package)

    matches = matcher.match("A I is not A P I")

    assert [m.term for m in matches] == ["AI", "API"]


def test_spoken_acronym_alias_matches_phonetic_phrase():
    package = make_package(
        [
            make_term(
                canonical_en="API",
                pos="acronym",
                aliases=["ai pi ai"],
                priority=1,
            )
        ]
    )
    matcher = Matcher(package)

    assert [m.term for m in matcher.match("Call the ai pi ai now.")] == ["API"]


def test_fuzzy_is_opt_in():
    package = make_package([make_term(canonical_en="transformer", priority=1)])

    strict = Matcher(package)
    fuzzy = Matcher(package, MatcherConfig(fuzzy=True))

    assert strict.match("The transfomer works.") == []
    assert [m.term for m in fuzzy.match("The transfomer works.")] == ["transformer"]


def test_fuzzy_ignores_short_terms():
    package = make_package([make_term(canonical_en="bias", priority=1)])
    matcher = Matcher(
        package, MatcherConfig(fuzzy=True, fuzzy_min_length=5)
    )

    assert matcher.match("The bais is clear.") == []
    assert matcher.match("The bias is clear.") != []


def test_fuzzy_does_not_match_unrelated_word():
    package = make_package([make_term(canonical_en="model", priority=1)])
    matcher = Matcher(package, MatcherConfig(fuzzy=True))

    assert matcher.match("The modal dialog.") == []


def test_reports_ambiguous_and_sense_count():
    term = make_term(
        canonical_en="bias",
        is_ambiguous=True,
        senses=[
            {"ordinal": 1, "domain_tag": "tech", "translation_pt": "viés", "definition_pt": "a"},
            {"ordinal": 2, "domain_tag": "general", "translation_pt": "tendência", "definition_pt": "b"},
        ],
    )
    matcher = Matcher(make_package([term]))

    matches = matcher.match("There is bias in the data.")

    assert matches[0].ambiguous is True
    assert matches[0].sense_count == 2


def test_stoplisted_term_suppressed_without_context():
    term = make_term(
        canonical_en="model",
        stoplisted=True,
        context_hints=["train", "dataset"],
        priority=1,
    )
    matcher = Matcher(make_package([term]))

    assert matcher.match("The model is fast.") == []


def test_stoplisted_term_confirmed_by_context():
    term = make_term(
        canonical_en="model",
        stoplisted=True,
        context_hints=["train", "dataset"],
        priority=1,
    )
    matcher = Matcher(make_package([term]))

    matches = matcher.match("The model is fast.", context="train the model")

    assert [m.term for m in matches] == ["model"]


def test_match_is_case_and_punctuation_insensitive():
    package = make_package([make_term(canonical_en="transformer", priority=1)])
    matcher = Matcher(package)

    matches = matcher.match("Transformer-based, isn't it?")

    assert [m.term for m in matches] == ["transformer"]


def test_cooldown_suppresses_repeated_term():
    clock = FakeClock()
    package = make_package([make_term(canonical_en="token", priority=1)])
    matcher = Matcher(package, MatcherConfig(cooldown_s=120.0), clock=clock)

    assert len(matcher.match("token")) == 1
    assert matcher.match("token") == []

    clock.advance(121.0)
    assert len(matcher.match("token")) == 1


def test_budget_limits_popups_per_minute():
    clock = FakeClock()
    terms = [make_term(canonical_en=w, priority=1) for w in ("alpha", "beta", "gamma")]
    matcher = Matcher(
        make_package(terms), MatcherConfig(max_popups_per_minute=2), clock=clock
    )

    matches = matcher.match("alpha beta gamma")

    assert [m.term for m in matches] == ["alpha", "beta"]


def test_reset_clears_policy_state():
    package = make_package([make_term(canonical_en="token", priority=1)])
    matcher = Matcher(package)

    matcher.match("token")
    matcher.reset()

    assert len(matcher.match("token")) == 1


def test_match_offsets_point_percent_into_normalized_text():
    package = make_package([make_term(canonical_en="neural network", priority=1)])
    matcher = Matcher(package)

    matches = matcher.match("A neural network learns.")
    text = "a neural network learns"

    assert matches[0].surface == text[matches[0].start_idx : matches[0].end_idx]


def test_real_seed_package_recognizes_known_terms():
    package = load_package(PACKAGE_DIR)
    matcher = Matcher(package)

    matches = matcher.match("We applied gradient descent to train the model.", context="train")
    found = {m.term for m in matches}

    assert "gradient descent" in found
    assert "model" in found


def test_real_seed_package_ignores_bare_stoplisted_term():
    package = load_package(PACKAGE_DIR)
    matcher = Matcher(package)

    matches = matcher.match("This layer is nice.")

    assert all(m.term != "layer" for m in matches)
