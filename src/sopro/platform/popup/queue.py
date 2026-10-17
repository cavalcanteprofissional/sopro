"""Fila de pop-ups visíveis (docs/02 §8, RF-20).

Camada de apresentação: mantém no máximo ``max_visible`` cartões simultâneos e
registra qual cartão saiu de cena para o overlay atualizar a tela. A **política**
de exibição (cooldown por termo e orçamento por minuto) fica no ``Matcher``
(docs/02 §4.5), que só emite termos elegíveis — evitando duas fontes de verdade.

O tempo é injetado como segundos monotônicos para ser testável.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class PopupError(ValueError):
    """Configuração de fila inválida."""


class PopupDecision(str, Enum):
    """Resultado de oferecer um item à fila de cartões visíveis."""

    SHOWN = "shown"
    REPLACED_OLDEST = "replaced-oldest"
    DROPPED_DUPLICATE = "dropped-duplicate"


@dataclass(frozen=True)
class PopupItem:
    """Cartão a exibir. ``key`` identifica o termo (deduplicação)."""

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
    """Gerencia os cartões visíveis: limite de simultâneos e substituição."""

    def __init__(self, *, max_visible: int = 3) -> None:
        if max_visible < 1:
            raise PopupError("max_visible deve ser >= 1")
        self._max_visible = max_visible
        self._active: deque[_Active] = deque()

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
        """Exibe ``item`` em ``now``, substituindo o mais antigo se estiver cheio."""
        if self.is_active(item.key):
            return OfferResult(PopupDecision.DROPPED_DUPLICATE)

        evicted: PopupItem | None = None
        if len(self._active) >= self._max_visible:
            evicted = self._active.popleft().item

        self._active.append(_Active(item, now))
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
