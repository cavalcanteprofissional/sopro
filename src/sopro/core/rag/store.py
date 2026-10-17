"""Persistência dos embeddings das acepções (``sense_vec``) e carga para o resolvedor.

Vetoriza as acepções de um domínio importado e as grava no banco, evitando recalcular
a cada execução (docs/02 §6–§7). A carga devolve um mapeamento pronto para alimentar
o :class:`~sopro.core.rag.resolver.SenseResolver`.

Os vetores são guardados como ``float32`` (blob) numa tabela comum ``sense_vec`` em vez
de uma tabela virtual de uma extensão (ex.: ``sqlite-vec``): mantém o núcleo portátil e
sem necessidade de carregar extensões nativas no SQLite do Python.
"""

from __future__ import annotations

from sopro.core.glossary.package import DomainPackage
from sopro.core.rag.embeddings import EmbeddingProvider, default_embedder
from sopro.core.rag.resolver import sense_key, sense_text
from sopro.core.repo import Repository


def embed_domain(
    repo: Repository,
    package: DomainPackage,
    domain_id: int,
    embedder: EmbeddingProvider | None = None,
) -> int:
    """Vetoriza e persiste as acepções do domínio; devolve a quantidade vetorizada."""
    embedder = embedder or default_embedder()
    items: list[tuple[int, str]] = []
    for term in package.terms:
        record = repo.get_term_by_canonical(domain_id, term.canonical_en)
        if record is None:
            continue
        for sense in repo.list_senses(record.id):
            items.append((sense.id, sense_text(sense)))
    if not items:
        return 0
    vectors = embedder.embed([text for _sense_id, text in items])
    for (sense_id, _text), vector in zip(items, vectors):
        repo.upsert_sense_vector(sense_id, embedder.name, embedder.dim, vector)
    return len(items)


def load_vectors(
    repo: Repository,
    package: DomainPackage,
    domain_id: int,
    model: str | None = None,
) -> dict[object, list[float]]:
    """Carrega vetores persistidos como ``{(canonical, ordinal): vetor}``."""
    vectors: dict[object, list[float]] = {}
    for term in package.terms:
        record = repo.get_term_by_canonical(domain_id, term.canonical_en)
        if record is None:
            continue
        for sense in repo.list_senses(record.id):
            vector = repo.get_sense_vector(sense.id, model=model)
            if vector is not None:
                vectors[sense_key(term.canonical_en, sense)] = vector
    return vectors
