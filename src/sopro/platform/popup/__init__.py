"""Overlay de pop-up (sem foco, sempre no topo) por plataforma.

A fila e as regras de exibição (cooldown, orçamento, limite de cartões) são puras
e testáveis em `queue`; a renderização concreta por SO é adicionada aqui.
"""

from sopro.platform.popup.queue import (
    PopupDecision,
    PopupError,
    PopupItem,
    PopupQueue,
    OfferResult,
)

__all__ = [
    "OfferResult",
    "PopupDecision",
    "PopupError",
    "PopupItem",
    "PopupQueue",
]
