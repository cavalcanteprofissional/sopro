"""Deduplicação de fala capturada simultaneamente do sistema e do microfone."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from sopro.core.text.normalize import normalize

DEFAULT_DEDUP_WINDOW_S = 2.0


class SourceDeduplicator:
    """Suprime a mesma fala/termo vindo de outra fonte dentro de uma janela curta.

    O sistema captura o eco do microfone e vice-versa. A primeira fonte a concluir
    o trecho vence; a segunda é descartada. Repetições legítimas da **mesma** fonte
    continuam sujeitas ao cooldown normal do ``Matcher``.
    """

    def __init__(
        self,
        window_s: float = DEFAULT_DEDUP_WINDOW_S,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window_s = max(0.0, float(window_s))
        self._clock = clock
        self._transcripts: deque[tuple[float, str, str]] = deque()
        self._terms: deque[tuple[float, str, str]] = deque()

    @property
    def window_s(self) -> float:
        return self._window_s

    def _purge(self, now: float) -> None:
        cutoff = now - self._window_s
        while self._transcripts and self._transcripts[0][0] < cutoff:
            self._transcripts.popleft()
        while self._terms and self._terms[0][0] < cutoff:
            self._terms.popleft()

    def duplicate_transcript(self, source: str, text: str) -> bool:
        """Marca e informa se ``text`` já veio de outra fonte na janela."""
        key = normalize(text)
        if not key:
            return False
        now = self._clock()
        self._purge(now)
        if any(old_key == key and old_source != source for _t, old_key, old_source in self._transcripts):
            return True
        self._transcripts.append((now, key, source))
        return False

    def duplicate_term(self, source: str, term: str) -> bool:
        """Suprime o mesmo termo detectado por outra fonte na janela."""
        key = normalize(term)
        if not key:
            return False
        now = self._clock()
        self._purge(now)
        if any(old_key == key and old_source != source for _t, old_key, old_source in self._terms):
            return True
        self._terms.append((now, key, source))
        return False

    def reset(self) -> None:
        self._transcripts.clear()
        self._terms.clear()
