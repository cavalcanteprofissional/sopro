"""Normalização e tokenização de texto transcrito (docs/02 §4, passo 1).

A normalização prepara o texto para o casamento de termos: minúsculas, hífens e
sublinhados viram espaço, pontuação é removida e espaços são recolhidos. A
tokenização devolve tokens com deslocamentos (offsets) no texto normalizado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_HYPHEN_RE = re.compile(r"[-_]")
_KEEP_RE = re.compile(r"[^a-z0-9\s]")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class Token:
    """Um token normalizado com sua posição ``[start, end)``."""

    text: str
    start: int
    end: int


def normalize(text: str) -> str:
    """Normaliza o texto para casamento (docs/02 §4, passo 1)."""
    lowered = text.lower()
    dehyphenated = _HYPHEN_RE.sub(" ", lowered)
    stripped = _KEEP_RE.sub(" ", dehyphenated)
    return _WS_RE.sub(" ", stripped).strip()


def tokenize(normalized: str) -> tuple[Token, ...]:
    """Tokeniza um texto já normalizado, com offsets."""
    return tuple(
        Token(match.group(0), match.start(), match.end())
        for match in _TOKEN_RE.finditer(normalized)
    )


def normalize_tokens(text: str) -> tuple[Token, ...]:
    """Atalho: normaliza e tokeniza em uma única chamada."""
    return tokenize(normalize(text))
