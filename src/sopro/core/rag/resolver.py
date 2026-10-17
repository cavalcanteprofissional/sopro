"""Resolvedor de acepções em cascata (docs/02 §3.4).

Escolhe **qual** sentido de um termo ambíguo mostrar, seguindo a cascata:
acepção única → etiqueta de domínio → similaridade vetorial → LLM (só quando a
pontuação fica abaixo do limiar). O LLM nunca participa de toda frase — só decide
ambiguidade (docs/02 §3 princípio central).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from sopro.core.glossary.package import Sense, Term
from sopro.core.rag.embeddings import EmbeddingProvider, cosine, default_embedder

RESOLVE_METHODS = ("single_sense", "domain_tag", "vector", "llm")
DEFAULT_THRESHOLD = 0.25
VECTOR_FALLBACK_SCORE = 0.0


@dataclass(frozen=True)
class Resolution:
    """Escolha de uma acepção, com pontuação e método da cascata."""

    sense: Sense
    score: float
    method: str


class SenseChooser(Protocol):
    """Contrato do passo opcional de LLM (escolhe entre candidatas).

    Devolve o índice da acepção escolhida ou ``None`` se não conseguir decidir
    (o resolvedor mantém então a melhor acepção vetorial).
    """

    def choose(
        self, term: Term, context: str, candidates: Sequence[Sense]
    ) -> int | None: ...


def sense_text(sense: Sense) -> str:
    """Texto usado para vetorizar uma acepção."""
    parts = [sense.translation_pt, sense.definition_pt, sense.domain_tag]
    if sense.example_en:
        parts.append(sense.example_en)
    return " ".join(part for part in parts if part)


def sense_key(canonical_en: str, sense: Sense) -> object:
    """Chave estável de uma acepção no pacote em memória."""
    return (canonical_en, sense.ordinal)


class SenseResolver:
    """Escolhe a acepção de um termo dado o contexto transcrito."""

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider | None = None,
        domain_tag: str | None = None,
        llm: SenseChooser | None = None,
        threshold: float = DEFAULT_THRESHOLD,
        vectors: Mapping[object, Sequence[float]] | None = None,
    ) -> None:
        self._embedder = embedder or default_embedder()
        self._domain_tag = domain_tag
        self._llm = llm
        self._threshold = threshold
        self._known = {key: list(vector) for key, vector in (vectors or {}).items()}
        self._cache: dict[object, list[float]] = {}

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    def _vector_for(self, key: object, text: str) -> list[float]:
        if key in self._cache:
            return self._cache[key]
        vector = self._known.get(key) or self._embedder.embed([text])[0]
        self._cache[key] = vector
        return vector

    def resolve(self, term: Term, context: str) -> Resolution | None:
        """Devolve a acepção escolhida para ``term`` dentro de ``context``."""
        senses = term.senses
        if not senses:
            return None
        if len(senses) == 1:
            return Resolution(senses[0], 1.0, "single_sense")

        candidates = list(senses)
        if self._domain_tag:
            tagged = list(term.domain_senses(self._domain_tag))
            if len(tagged) == 1:
                return Resolution(tagged[0], 0.9, "domain_tag")
            if len(tagged) > 1:
                candidates = tagged

        context_vector = self._embedder.embed([context])[0]
        best: Sense | None = None
        best_score = VECTOR_FALLBACK_SCORE
        for sense in candidates:
            key = sense_key(term.canonical_en, sense)
            score = cosine(context_vector, self._vector_for(key, sense_text(sense)))
            if best is None or score > best_score:
                best, best_score = sense, score

        if self._llm is not None and best_score < self._threshold:
            index = self._choose(term, context, candidates)
            if index is not None:
                return Resolution(candidates[index], best_score, "llm")

        if best is not None:
            return Resolution(best, best_score, "vector")
        return Resolution(
            min(candidates, key=lambda s: s.ordinal), VECTOR_FALLBACK_SCORE, "vector"
        )

    def _choose(
        self, term: Term, context: str, candidates: Sequence[Sense]
    ) -> int | None:
        """Chama o LLM de forma tolerante a falhas; devolve índice válido ou None."""
        try:
            index = self._llm.choose(term, context, candidates)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001 - LLM é exceção opcional; nunca derruba o pipeline
            return None
        if index is None or not 0 <= index < len(candidates):
            return None
        return index
