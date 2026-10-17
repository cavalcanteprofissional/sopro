"""Dica de vocabulário para o STT a partir do glossário (docs/02 §5, docs/05 A2).

Monta a lista de termos de maior prioridade do domínio, truncada ao limite aceito
pelo modelo. Compartilhada pelo benchmark e pelo pipeline em tempo real.
"""

from __future__ import annotations

from sopro.core.glossary.package import DomainPackage

DEFAULT_VOCAB_LIMIT = 50


def vocabulary_hint(
    package: DomainPackage, limit: int = DEFAULT_VOCAB_LIMIT
) -> tuple[str, ...]:
    """Termos de maior prioridade do pacote (menor ``priority`` primeiro)."""
    if limit <= 0:
        return ()
    ordered = sorted(package.terms, key=lambda term: term.priority)
    return tuple(term.canonical_en for term in ordered[:limit])
