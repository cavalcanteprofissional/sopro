"""Fila de pop-ups com cooldown e orçamento por minuto (docs/02 §8, RF-19/20).

Lógica pura (sem interface gráfica): decide *o que* exibir e quando, enquanto a
camada de overlay (`overlay.py`) cuida da renderização. O tempo é injetado como
segundos monotônicos para ser testável.

Regras:
- **cooldown** por termo (RF-19, RN-02): o mesmo termo não reaparece dentro do
  intervalo configurado;
- **orçamento por minuto** (RF-19): no máximo N pop-ups em qualquer janela de 60 s;
- **máximo simultâneo** (RF-20, docs/02 §131): novos cartões substituem o mais
  antigo quando o limite de cartões visíveis é atingido.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum

BUDGET_WINDOW_S = 60.0


class PopupError(ValueError):
    """Configuração de fila inválida."""


class PopupDecision(str, Enum):
    """Resultado de oferecer um item à fila."""

    SHOWN = "shown"
    REPLACED_OLDEST = "replaced-oldest"
    DROPPED_COOLDOWN = "dropped-cooldown"
    DROPPED_BUDGET = "dropped-budget"
    DROPPED_DUPLICATE = "dropped-duplicate"


@dataclass(frozen=True)
class PopupItem:
    """Cartão a exibir. ``key`` identifica o termo (cooldown/deduplicação)."""

    key: str
    payload: object = None


@dataclass(frozen=True)
class OfferResult:
    """Decisão tomada e, se houve substituição, o item que saiu de cena."""

    decision: PopupDecision
    evicted: PopupItem | None = None


@dataclass
class _Active:
    item: PopupItem
    shown_at: float


class PopupQueue:
    """Fila de cartões com cooldown, orçamento e limite de simultâneos."""

    def __init__(
        self,
        *,
        max_visible: int = 3,
        cooldown_s: float = 30.0,
        budget_per_minute: int = 6,
    ) -> None:
        if max_visible < 1:
            raise PopupError("max_visible deve ser >= 1")
        if cooldown_s < 0:
            raise PopupError("cooldown_s não pode ser negativo")
        if budget_per_minute < 0:
            raise PopupError("budget_per_minute não pode ser negativo")
        self._max_visible = max_visible
        self._cooldown_s = cooldown_s
        self._budget = budget_per_minute
        self._active: deque[_Active] = deque()
        self._last_shown: dict[str, float] = {}
        self._shown_times: deque[float] = deque()

    # -- consulta -----------------------------------------------------------
    @property
    def max_visible(self) -> int:
        return self._max_visible

    def active_items(self) -> tuple[PopupItem, ...]:
        return tuple(a.item for a in self._active)

    def active_count(self) -> int:
        return len(self._active)

    def is_active(self, key: str) -> bool:
        return any(a.item.key == key for a in self._active)

    # -- mutação ------------------------------------------------------------
    def offer(self, item: PopupItem, now: float) -> OfferResult:
        """Tenta exibir ``item`` em ``now`` (segundos monotônicos)."""
        if self.is_active(item.key):
            return OfferResult(PopupDecision.DROPPED_DUPLICATE)
        if self._on_cooldown(item.key, now):
            return OfferResult(PopupDecision.DROPPED_COOLDOWN)
        if not self._budget_available(now):
            return OfferResult(PopupDecision.DROPPED_BUDGET)

        evicted: PopupItem | None = None
        if len(self._active) >= self._max_visible:
            evicted = self._active.popleft().item

        self._active.append(_Active(item, now))
        self._last_shown[item.key] = now
        self._shown_times.append(now)
        decision = (
            PopupDecision.REPLACED_OLDEST if evicted is not None else PopupDecision.SHOWN
        )
        return OfferResult(decision, evicted)

    def close(self, key: str) -> bool:
        """Remove o cartão ``key`` (clique/fechamento). Retorna se existia."""
        before = len(self._active)
        self._active = deque(a for a in self._active if a.item.key != key)
        return len(self._active) < before

    def expire(self, now: float, duration_s: float) -> tuple[PopupItem, ...]:
        """Remove e devolve os cartões cujo tempo de exibição já passou."""
        expired = tuple(a.item for a in self._active if a.shown_at + duration_s <= now)
        if expired:
            self._active = deque(
                a for a in self._active if a.shown_at + duration_s > now
            )
        return expired

    # -- interno ------------------------------------------------------------
    def _on_cooldown(self, key: str, now: float) -> bool:
        last = self._last_shown.get(key)
        return last is not None and (now - last) < self._cooldown_s

    def _budget_available(self, now: float) -> bool:
        self._prune_budget(now)
        return len(self._shown_times) < self._budget

    def _prune_budget(self, now: float) -> None:
        cutoff = now - BUDGET_WINDOW_S
        while self._shown_times and self._shown_times[0] <= cutoff:
            self._shown_times.popleft()
