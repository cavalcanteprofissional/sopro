"""Dica de vocabulário para o STT a partir do glossário (docs/02 §5, docs/05 A2).

Monta a lista de termos do domínio priorizados por ``priority``, incluindo aliases
curtos, truncada ao limite de tokens aceito pelo modelo (~224).
"""

from __future__ import annotations

from sopro.core.glossary.package import DomainPackage
from sopro.core.text.normalize import normalize

DEFAULT_VOCAB_LIMIT = 220
MAX_TOKEN_CHARS = 24


def _token_count(text: str) -> int:
    """Aproximação conservadora do número de tokens do Whisper."""
    if not text:
        return 0
    return max(1, len(text) // 4 + text.count(" ") + 1)


def vocabulary_hint(
    package: DomainPackage,
    limit: int = DEFAULT_VOCAB_LIMIT,
    active_tracks: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Termos e aliases prioritários do pacote, truncados por ~limite de tokens.

    Termos das trilhas ativas vêm antes dos genéricos, preservando ``priority``
    dentro de cada grupo.
    """
    if limit <= 0:
        return ()
    selected = set(active_tracks)

    def order(term) -> tuple[int, int, str]:
        in_track = bool(selected) and bool(set(term.tracks) & selected)
        return (0 if in_track else 1, term.priority, term.canonical_en)

    ordered = sorted(package.terms, key=order)
    seen: set[str] = set()
    hint: list[str] = []
    tokens = 0
    for term in ordered:
        candidates = [term.canonical_en]
        for alias in term.aliases:
            if alias and len(alias) <= MAX_TOKEN_CHARS:
                candidates.append(alias)
        for candidate in candidates:
            key = normalize(candidate).replace(" ", " ")
            if not key or key in seen:
                continue
            tcount = _token_count(candidate)
            if tokens + tcount > limit:
                continue
            hint.append(candidate)
            seen.add(key)
            tokens += tcount
    return tuple(hint)
