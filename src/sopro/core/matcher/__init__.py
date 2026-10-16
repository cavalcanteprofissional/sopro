"""Detecção de termos no texto transcrito (n-gramas, aliases, stoplist)."""

from sopro.core.matcher.matcher import (
    DEFAULT_COOLDOWN_S,
    DEFAULT_MAX_POPUPS_PER_MINUTE,
    MAX_NGRAM,
    Match,
    Matcher,
    MatcherConfig,
    pluralize,
)

__all__ = [
    "DEFAULT_COOLDOWN_S",
    "DEFAULT_MAX_POPUPS_PER_MINUTE",
    "MAX_NGRAM",
    "Match",
    "Matcher",
    "MatcherConfig",
    "pluralize",
]
