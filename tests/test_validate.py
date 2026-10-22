"""Testes do validador de pacotes (checklist de docs/07 §6)."""

from pathlib import Path

from sopro.core.glossary.package import load_package
from sopro.core.glossary.validate import _word_count, validate_package

from tests.test_glossary_package import make_package, make_term

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "data" / "domains" / "tech-en-pt"


def codes(issues):
    return [i.code for i in issues]


def test_real_seed_package_has_no_errors():
    report = validate_package(load_package(PACKAGE_DIR))

    assert report.ok, [i.format() for i in report.errors]
    assert codes(report.errors) == []
    assert report.stats["term_count"] >= 50
    assert report.stats["sense_count"] >= report.stats["term_count"]


def test_real_seed_package_reports_known_pending_items():
    report = validate_package(load_package(PACKAGE_DIR))
    warning_codes = codes(report.warnings)

    assert "W_REVIEW_PENDING" in warning_codes
    assert "W_LICENSE_PLACEHOLDER" not in warning_codes


def test_duplicate_canonical_en_is_error():
    report = validate_package(make_package([make_term(canonical_en="token"), make_term(canonical_en="Token")]))
    assert "E_DUPLICATE_TERM" in codes(report.errors)


def test_ambiguous_without_domain_sense_is_error():
    term = make_term(
        canonical_en="ambiguous",
        is_ambiguous=True,
        context_hints=["hint"],
        senses=[
            {"ordinal": 1, "domain_tag": "general", "translation_pt": "a", "definition_pt": "a"},
        ],
    )
    report = validate_package(make_package([term]))
    assert "E_AMBIGUOUS_WITHOUT_DOMAIN_SENSE" in codes(report.errors)


def test_alias_colliding_with_stoplist_warns():
    term = make_term(canonical_en="network", aliases=["model"])
    report = validate_package(make_package([term], stoplist=["model"]))
    assert "W_ALIAS_STOPLIST" in codes(report.warnings)


def test_stoplisted_without_context_hints_warns():
    term = make_term(canonical_en="layer", stoplisted=True, context_hints=[])
    report = validate_package(make_package([term]))
    assert "W_NO_CONTEXT_HINTS" in codes(report.warnings)


def test_invalid_pos_is_error():
    report = validate_package(make_package([make_term(pos="pronoun")]))
    assert "E_INVALID_POS" in codes(report.errors)


def test_priority_out_of_range_is_error():
    report = validate_package(make_package([make_term(priority=9)]))
    assert "E_PRIORITY_RANGE" in codes(report.errors)


def test_definition_too_long_is_error():
    long_definition = " ".join(f"palavra{i}" for i in range(30))
    term = make_term(
        senses=[
            {"ordinal": 1, "domain_tag": "tech", "translation_pt": "t", "definition_pt": long_definition}
        ]
    )
    report = validate_package(make_package([term]))
    assert "E_DEFINITION_TOO_LONG" in codes(report.errors)


def test_term_without_senses_is_error():
    report = validate_package(make_package([make_term(senses=[])]))
    assert "E_NO_SENSES" in codes(report.errors)


def test_generated_term_not_reviewed_is_error():
    term = make_term(source="gerado", needs_review=False)
    report = validate_package(make_package([term]))
    assert "E_GENERATED_NOT_REVIEWED" in codes(report.errors)


def test_missing_manifest_authors_is_error():
    report = validate_package(make_package([make_term()], authors=[]))
    assert "E_MANIFEST_AUTHORS" in codes(report.errors)


def test_word_count_boundary():
    assert _word_count("") == 0
    assert _word_count("uma duas três") == 3
