"""Candidatos fora do glossário e limite de taxa próprio (docs/02 §4.6).

Heurística **conservadora**: procura substantivos/sintagmas raros (frequência baixa
numa lista geral de inglês embutida) que não estejam no glossário ativo nem na
stoplist do domínio. É a matéria-prima do caminho LLM (``GeneratedEntryService``),
com um :class:`RateLimiter` para não estourar o plano gratuito.

A lista de palavras comuns é um proxy simples de frequência — suficiente para
reduzir ruído, não um léxico completo.
"""

from __future__ import annotations

import re
import time
from collections import deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*")

DEFAULT_MIN_LENGTH = 4
DEFAULT_MAX_NGRAM = 3
DEFAULT_LIMIT = 3

# Palavras muito comuns em inglês (proxy de frequência): nunca são candidatas.
COMMON_WORDS = frozenset(
    """
    about above after again against all also always among another any anyone anything
    around because been before being below between both bring call called came can cannot
    come could day did does doing done down during each else enough even ever every everyone
    everything example fact far few find first found from further gave get give given goes
    going gone good got great had has have having here hers herself him himself his how
    however into its itself just keep kind know known last later least left less like likely
    little long look looking made make making many may maybe mean means might more most much
    must near need never new next none nor not nothing now number off often once one only
    other others our ours ourselves out over own part particular past people perhaps place
    point put quite rather really right said same saw say says see seem seen several she
    should show side since small so some someone something sometimes soon still such sure
    take taken takes than that the their theirs them themselves then there these they thing
    things think this those though through thus time today together too took toward under
    until upon use used using very want wanted was way well went were what whatever when
    where whether which while who whole whom whose why will with within without work would
    year yes yet you your yours yourself
    """.split()
)


@dataclass(frozen=True)
class Candidate:
    """Um candidato fora do glossário, com posição e pontuação de raridade."""

    surface: str
    start_idx: int
    end_idx: int
    score: float


def _tokens(text: str) -> list[tuple[str, int, int]]:
    return [(m.group(0), m.start(), m.end()) for m in _WORD_RE.finditer(text)]


def _eligible(token: str, known: frozenset[str], stoplist: frozenset[str], min_length: int) -> bool:
    low = token.lower()
    return (
        len(low) >= min_length
        and low not in COMMON_WORDS
        and low not in stoplist
        and low not in known
    )


def _score(surface: str) -> float:
    words = surface.split()
    score = 2.0 * len(words) + sum(len(w) for w in words) / max(len(words), 1)
    if surface[:1].isupper() or surface.isupper():
        score += 1.5
    return score


def extract_candidates(
    text: str,
    known: Iterable[str] = (),
    *,
    stoplist: Iterable[str] = (),
    min_length: int = DEFAULT_MIN_LENGTH,
    max_ngram: int = DEFAULT_MAX_NGRAM,
    limit: int = DEFAULT_LIMIT,
) -> list[Candidate]:
    """Devolve até ``limit`` candidatos não sobrepostos, do mais raro ao menos."""
    known_set = frozenset(item.lower() for item in known)
    stop_set = frozenset(item.lower() for item in stoplist)
    tokens = _tokens(text)
    found: list[Candidate] = []
    for index, (token, start, _end) in enumerate(tokens):
        if not _eligible(token, known_set, stop_set, min_length):
            continue
        for size in range(1, max_ngram + 1):
            if index + size > len(tokens):
                break
            window = tokens[index : index + size]
            if size > 1 and not _eligible(
                window[-1][0], known_set, stop_set, min_length
            ):
                break
            surface = " ".join(item[0] for item in window)
            if size > 1 and surface.lower() in known_set:
                break
            found.append(
                Candidate(
                    surface=surface,
                    start_idx=window[0][1],
                    end_idx=window[-1][2],
                    score=_score(surface),
                )
            )
    return _select_non_overlapping(found, limit)


def _select_non_overlapping(candidates: Sequence[Candidate], limit: int) -> list[Candidate]:
    """Escolhe por "maior casamento primeiro" da esquerda para a direita (docs/02 §4.2)."""
    ordered = sorted(
        candidates,
        key=lambda c: (c.start_idx, -(c.end_idx - c.start_idx), -c.score),
    )
    chosen: list[Candidate] = []
    cursor = -1
    for candidate in ordered:
        if candidate.start_idx < cursor:
            continue
        chosen.append(candidate)
        cursor = candidate.end_idx
        if len(chosen) >= limit:
            break
    return chosen


class RateLimiter:
    """Limite de taxa por janela deslizante de 60 s (sem dependências)."""

    def __init__(self, max_per_minute: int, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._max = max(int(max_per_minute), 0)
        self._clock = clock
        self._events: deque[float] = deque()

    def allow(self, now: float | None = None) -> bool:
        """Consome uma permissão se houver; devolve ``True`` quando permitido."""
        moment = self._clock() if now is None else now
        cutoff = moment - 60.0
        while self._events and self._events[0] < cutoff:
            self._events.popleft()
        if len(self._events) >= self._max:
            return False
        if self._max > 0:
            self._events.append(moment)
        return self._max > 0
