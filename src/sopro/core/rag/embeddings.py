"""Embeddings locais para desambiguação de acepções (docs/02 §3.4, Fase 3).

Contrato de embedding com duas implementações:

- :class:`HashingEmbedder` — determinístico, sem dependências, offline por padrão;
  usado como base do resolvedor e nos testes.
- :class:`SentenceTransformerEmbedder` — opcional, carrega sob demanda (extra ``rag``).

Os vetores são L2-normalizados, então similaridade = produto escalar.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterable, Sequence
from typing import Protocol

_TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    {
        "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "in",
        "is", "it", "of", "on", "or", "that", "the", "this", "to", "with",
    }
)


class EmbeddingError(Exception):
    """Falha ao gerar embeddings."""


class EmbeddingProvider(Protocol):
    """Contrato de um provedor de embeddings."""

    name: str
    dim: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


def tokenize(text: str) -> list[str]:
    """Tokens simples em minúsculas, sem stopwords."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Similaridade cosseno entre dois vetores normalizados."""
    if len(a) != len(b):
        raise ValueError("vetores de dimensões diferentes")
    return sum(x * y for x, y in zip(a, b))


class HashingEmbedder:
    """Embedding por *hashing trick*: tokens espalhados em ``dim`` buckets com sinal."""

    def __init__(self, dim: int = 128) -> None:
        if dim <= 0:
            raise ValueError("dim deve ser positivo")
        self.name = f"hashing-v1-{dim}"
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            value = int.from_bytes(digest[:8], "big")
            index = value % self.dim
            sign = 1.0 if digest[8] % 2 == 0 else -1.0
            vector[index] += sign
        return _normalize(vector)


class SentenceTransformerEmbedder:
    """Embedding real via ``sentence-transformers`` (extra ``rag``; carregado sob demanda)."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - dependência opcional
            raise EmbeddingError(
                "sentence-transformers não instalado (extra 'rag')"
            ) from exc
        self._model = SentenceTransformer(model_name)
        self.name = model_name
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = self._model.encode(list(texts), convert_to_numpy=True)
        return [_normalize([float(v) for v in row]) for row in vectors]


def default_embedder() -> HashingEmbedder:
    """Embedder padrão: determinístico, offline e sem dependências."""
    return HashingEmbedder()


def create_embedder(name: str = "hashing") -> EmbeddingProvider:
    """Fábrica de embedders; ``sentence-transformers`` só se instalado."""
    if name in ("hashing", "hashing-v1"):
        return HashingEmbedder()
    if name.startswith("sentence-transformers") or name == "minilm":
        model = (
            "sentence-transformers/all-MiniLM-L6-v2" if name == "minilm" else name
        )
        return SentenceTransformerEmbedder(model)
    raise EmbeddingError(f"modelo de embedding desconhecido: {name!r}")


def embed_texts(
    provider: EmbeddingProvider, texts: Iterable[str]
) -> list[list[float]]:
    """Convenience: embedde uma sequência de textos."""
    return provider.embed(list(texts))
