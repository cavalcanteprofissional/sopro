"""RAG: embeddings locais, busca vetorial e escolha de acepção (docs/02 §3.4, Fase 3).

O caminho rápido é o glossário local; este pacote resolve **ambiguidade** — escolhe
qual acepção de um termo mostrar — e prepara o terreno para o caminho LLM de termos
fora do glossário (Fase 3). Não participa de toda frase.
"""

from __future__ import annotations

from sopro.core.rag.embeddings import (
    EmbeddingError,
    EmbeddingProvider,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    cosine,
    create_embedder,
    default_embedder,
)
from sopro.core.rag.index import ScoredKey, SenseIndex
from sopro.core.rag.evaluate import (
    Case,
    EvalResult,
    Miss,
    ambiguous_cases,
    ambiguous_glossary,
    evaluate,
)
from sopro.core.rag.resolver import (
    DEFAULT_THRESHOLD,
    RESOLVE_METHODS,
    Resolution,
    SenseChooser,
    SenseResolver,
    sense_key,
    sense_text,
)
from sopro.core.rag.store import embed_domain, load_vectors

__all__ = [
    "Case",
    "DEFAULT_THRESHOLD",
    "EmbeddingError",
    "EmbeddingProvider",
    "EvalResult",
    "HashingEmbedder",
    "Miss",
    "RESOLVE_METHODS",
    "Resolution",
    "ScoredKey",
    "SenseChooser",
    "SenseIndex",
    "SenseResolver",
    "SentenceTransformerEmbedder",
    "ambiguous_cases",
    "ambiguous_glossary",
    "cosine",
    "create_embedder",
    "default_embedder",
    "embed_domain",
    "evaluate",
    "load_vectors",
    "sense_key",
    "sense_text",
]
