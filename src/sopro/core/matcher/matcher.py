"""Detecção de termos no texto transcrito (docs/02 §4).

O casamento é determinístico e puro (exceto pelo relógio injetável usado no
cooldown e no orçamento de pop-ups). Estratégia:

1. normalizar o texto (``core.text.normalize``);
2. gerar n-gramas de 1 a ``max_ngram`` tokens e casar o **maior** primeiro;
3. casar contra forma canônica, aliases e flexões comuns (plural por regra);
4. aplicar a lista de exclusão: termos comuns só disparam com dica de contexto;
5. aplicar cooldown por termo e orçamento de pop-ups por minuto.

A saída é uma lista de :class:`Match` prontos para o pop-up (docs/02 §3.3).
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from sopro.core.glossary.package import DomainPackage, Term
from sopro.core.text import normalize, tokenize

MAX_NGRAM = 4
DEFAULT_COOLDOWN_S = 120.0
DEFAULT_MAX_POPUPS_PER_MINUTE = 6
_WINDOW_S = 60.0


@dataclass(frozen=True)
class Match:
    """Um termo detectado em um trecho do texto (docs/02 §3.3)."""

    term: str
    surface: str
    start_idx: int
    end_idx: int
    ambiguous: bool
    sense_count: int


@dataclass(frozen=True)
class MatcherConfig:
    """Parâmetros do casamento e da política de exibição."""

    max_ngram: int = MAX_NGRAM
    cooldown_s: float = DEFAULT_COOLDOWN_S
    max_popups_per_minute: int = DEFAULT_MAX_POPUPS_PER_MINUTE


def pluralize(word: str) -> str:
    """Pluralizador conservador para flexões comuns do inglês."""
    if not word:
        return word
    if word.endswith("y") and len(word) > 1 and word[-2] not in "aeiou":
        return word[:-1] + "ies"
    if word.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    return word + "s"


def _term_keys(term: Term) -> set[tuple[str, ...]]:
    """Chaves de casamento do termo (canônica + aliases + plural)."""
    bases: list[tuple[str, ...]] = []
    canonical = tuple(t.text for t in tokenize(normalize(term.canonical_en)))
    if canonical:
        bases.append(canonical)
    for alias in term.aliases:
        tokens = tuple(t.text for t in tokenize(normalize(alias)))
        if tokens:
            bases.append(tokens)

    keys: set[tuple[str, ...]] = set()
    for base in bases:
        keys.add(base)
        plural = base[:-1] + (pluralize(base[-1]),)
        if plural != base:
            keys.add(plural)
    return keys


def _hint_keys(term: Term) -> tuple[tuple[str, ...], ...]:
    hints = []
    for hint in term.context_hints:
        tokens = tuple(t.text for t in tokenize(normalize(hint)))
        if tokens:
            hints.append(tokens)
    return tuple(hints)


class Matcher:
    """Casa termos de um pacote de domínio contra texto transcrito."""

    def __init__(
        self,
        package: DomainPackage,
        config: MatcherConfig | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._package = package
        self._config = config or MatcherConfig()
        self._clock = clock or time.monotonic
        self._terms_by_key: dict[tuple[str, ...], tuple[Term, ...]] = {}
        self._hints: dict[str, tuple[tuple[str, ...], ...]] = {}
        self._last_shown: dict[str, float] = {}
        self._recent: deque[float] = deque()
        self._build_index()

    @property
    def config(self) -> MatcherConfig:
        return self._config

    def _build_index(self) -> None:
        bucket: dict[tuple[str, ...], list[Term]] = {}
        for term in self._package.terms:
            self._hints[term.canonical_en] = _hint_keys(term)
            for key in _term_keys(term):
                bucket.setdefault(key, [])
                if term not in bucket[key]:
                    bucket[key].append(term)
        self._terms_by_key = {
            key: tuple(sorted(terms, key=lambda t: t.priority))
            for key, terms in bucket.items()
        }

    def _select(self, terms: tuple[Term, ...], context: tuple[str, ...]) -> Term | None:
        """Escolhe o termo elegível; termos na lista de exclusão exigem contexto."""
        for term in terms:
            if not term.stoplisted:
                return term
            if self._context_confirms(term, context):
                return term
        return None

    def _context_confirms(self, term: Term, context: tuple[str, ...]) -> bool:
        hints = self._hints.get(term.canonical_en, ())
        for hint in hints:
            length = len(hint)
            for start in range(len(context) - length + 1):
                if context[start : start + length] == hint:
                    return True
        return False

    def match(self, text: str, context: str | None = None) -> list[Match]:
        """Detecta termos em ``text``; ``context`` confirma termos da exclusão."""
        tokens = tokenize(normalize(text))
        context_tokens = (
            tuple(t.text for t in tokenize(normalize(context)))
            if context is not None
            else tuple(t.text for t in tokens)
        )

        detected: list[Match] = []
        i = 0
        total = len(tokens)
        while i < total:
            longest = min(self._config.max_ngram, total - i)
            advanced = False
            for length in range(longest, 0, -1):
                key = tuple(t.text for t in tokens[i : i + length])
                terms = self._terms_by_key.get(key)
                if terms is None:
                    continue
                term = self._select(terms, context_tokens)
                if term is not None:
                    detected.append(
                        Match(
                            term=term.canonical_en,
                            surface=" ".join(key),
                            start_idx=tokens[i].start,
                            end_idx=tokens[i + length - 1].end,
                            ambiguous=term.is_ambiguous,
                            sense_count=len(term.senses),
                        )
                    )
                i += length
                advanced = True
                break
            if not advanced:
                i += 1

        return self._apply_policy(detected)

    def _apply_policy(self, matches: list[Match]) -> list[Match]:
        now = self._clock()
        while self._recent and now - self._recent[0] >= _WINDOW_S:
            self._recent.popleft()

        emitted: list[Match] = []
        for match in matches:
            last = self._last_shown.get(match.term)
            if last is not None and now - last < self._config.cooldown_s:
                continue
            if len(self._recent) >= self._config.max_popups_per_minute:
                break
            self._last_shown[match.term] = now
            self._recent.append(now)
            emitted.append(match)
        return emitted

    def reset(self) -> None:
        """Limpa o estado de cooldown e de orçamento (ex.: nova sessão)."""
        self._last_shown.clear()
        self._recent.clear()
