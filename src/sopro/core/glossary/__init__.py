"""Carregamento, validação e gestão de pacotes de domínio (glossários)."""

from sopro.core.glossary.aggregate import (
    aggregate_packages,
    build_aggregate_from_repo,
    resolve_active_tracks,
)
from sopro.core.glossary.package import (
    DomainPackage,
    Manifest,
    Sense,
    Term,
    list_package_slugs,
    load_package,
)

__all__ = [
    "DomainPackage",
    "Manifest",
    "Sense",
    "Term",
    "aggregate_packages",
    "build_aggregate_from_repo",
    "list_package_slugs",
    "load_package",
    "resolve_active_tracks",
]
