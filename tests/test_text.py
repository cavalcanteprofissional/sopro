"""Testes de normalização e tokenização (sopro.core.text)."""

from sopro.core.text import Token, normalize, normalize_tokens, tokenize


def test_normalize_lowercases_and_collapses_spaces():
    assert normalize("  Hello   World  ") == "hello world"


def test_normalize_splits_hyphens_and_underscores():
    assert normalize("retrieval-augmented_generation") == "retrieval augmented generation"


def test_normalize_removes_punctuation():
    assert normalize("Model, (accuracy)!") == "model accuracy"


def test_normalize_empty_string():
    assert normalize("") == ""


def test_tokenize_returns_offsets():
    tokens = tokenize("hello world")
    assert tokens == (Token("hello", 0, 5), Token("world", 6, 11))


def test_tokenize_skips_extra_spaces():
    tokens = tokenize("a  b")
    assert [t.text for t in tokens] == ["a", "b"]
    assert tokens[1].start == 3


def test_normalize_tokens_combines_steps():
    tokens = normalize_tokens("RAG-based approach!")
    assert [t.text for t in tokens] == ["rag", "based", "approach"]
