"""Carregamento, validação e gestão de pacotes de domínio (glossários)."""

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
    "list_package_slugs",
    "load_package",
]
