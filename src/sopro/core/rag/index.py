"""Índice vetorial de acepções (busca por similaridade cosseno).

Mantém pares ``(chave, vetor)`` e devolve os ``k`` melhores para uma consulta.
Sem dependências: funciona com qualquer :class:`EmbeddingProvider` e vetores
L2-normalizados (similaridade = produto escalar).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from sopro.core.rag.embeddings import EmbeddingProvider, cosine, default_embedder


@dataclass(frozen=True)
class ScoredKey:
    """Resultado de uma busca no índice."""

    key: object
    score: float


class SenseIndex:
    """Índice de vetores com busca por cosseno."""

    def __init__(self, embedder: EmbeddingProvider | None = None) -> None:
        self._embedder = embedder or default_embedder()
        self._keys: list[object] = []
        self._vectors: list[list[float]] = []

    @property
    def embedder(self) -> EmbeddingProvider:
        return self._embedder

    def __len__(self) -> int:
        return len(self._keys)

    def clear(self) -> None:
        self._keys.clear()
        self._vectors.clear()

    def add(self, key: object, text: str) -> None:
        """Adiciona uma entrada embedindo o texto."""
        vector = self._embedder.embed([text])[0]
        self.add_vector(key, vector)

    def add_vector(self, key: object, vector: Sequence[float]) -> None:
        """Adiciona uma entrada já vetorizada (assumed normalizado)."""
        self._keys.append(key)
        self._vectors.append(list(vector))

    def build(self, entries: Iterable[tuple[object, str]]) -> None:
        """Reconstrói o índice a partir de pares ``(chave, texto)``."""
        items = list(entries)
        if not items:
            self.clear()
            return
        vectors = self._embedder.embed([text for _key, text in items])
        self._keys = [key for key, _text in items]
        self._vectors = vectors

    def search(self, query: str, k: int = 3) -> list[ScoredKey]:
        """Devolve as ``k`` melhores chaves para a consulta (ordem decrescente)."""
        if not self._vectors or k <= 0:
            return []
        query_vector = self._embedder.embed([query])[0]
        return self.search_vector(query_vector, k)

    def search_vector(
        self, query_vector: Sequence[float], k: int = 3
    ) -> list[ScoredKey]:
        """Busca por um vetor já calculado."""
        if not self._vectors or k <= 0:
            return []
        scored = [
            ScoredKey(key=key, score=cosine(query_vector, vector))
            for key, vector in zip(self._keys, self._vectors)
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:k]
