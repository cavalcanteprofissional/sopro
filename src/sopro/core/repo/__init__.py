"""Acesso a dados local (SQLite): detecções, histórico, cache e configurações.

Modelo de docs/02 §6. O núcleo expõe ``Database`` (conexão + migrações),
``Repository`` (domínios, termos, sessões, detecções, configurações e histórico)
e o importador/exportador de pacotes de domínio (docs/07 ⇄ SQLite).
"""

from sopro.core.repo.database import DEFAULT_DB_FILENAME, Database
from sopro.core.repo.export import history_to_csv, history_to_markdown
from sopro.core.repo.importer import (
    build_domain_package,
    export_package_json,
    import_package,
)
from sopro.core.repo.models import (
    DetectionRecord,
    DomainRecord,
    HistoryEntry,
    SenseInput,
    SenseRecord,
    SessionRecord,
    TermRecord,
)
from sopro.core.repo.repository import Repository

__all__ = [
    "DEFAULT_DB_FILENAME",
    "Database",
    "DetectionRecord",
    "DomainRecord",
    "HistoryEntry",
    "Repository",
    "SenseInput",
    "SenseRecord",
    "SessionRecord",
    "TermRecord",
    "build_domain_package",
    "export_package_json",
    "history_to_csv",
    "history_to_markdown",
    "import_package",
]
