"""Exportação do histórico em CSV e Markdown (docs/05 A6, RF-22).

Funções puras (sem banco): recebem entradas de histórico e devolvem texto. O
``Repository`` é quem consulta e grava em disco. O trecho de contexto é omitido
por padrão (privacidade, docs/02 §10).
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from io import StringIO

from sopro.core.repo.models import HistoryEntry

_CSV_FIELDS = [
    "at",
    "session_id",
    "term",
    "translation",
    "source",
    "method",
    "learned",
    "context_snippet",
]

_MD_HEADERS = ["Quando", "Sessão", "Termo", "Tradução", "Fonte", "Método", "Aprendido"]


def _learned(flag: bool) -> str:
    return "sim" if flag else "nao"


def history_to_csv(
    entries: Iterable[HistoryEntry], include_context: bool = False
) -> str:
    """Serializa o histórico em CSV (cabeçalho + linhas)."""
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(_CSV_FIELDS)
    for entry in entries:
        writer.writerow(
            [
                entry.at,
                "" if entry.session_id is None else entry.session_id,
                entry.term,
                entry.translation,
                entry.source,
                entry.method,
                _learned(entry.learned),
                (entry.context_snippet or "") if include_context else "",
            ]
        )
    return buffer.getvalue()


def history_to_markdown(
    entries: Iterable[HistoryEntry], include_context: bool = False
) -> str:
    """Serializa o histórico em uma tabela Markdown."""
    headers = list(_MD_HEADERS)
    if include_context:
        headers.append("Contexto")
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join("---" for _ in headers) + " |")
    for entry in entries:
        cells = [
            entry.at,
            "" if entry.session_id is None else str(entry.session_id),
            entry.term,
            entry.translation,
            entry.source,
            entry.method,
            _learned(entry.learned),
        ]
        if include_context:
            cells.append((entry.context_snippet or "").replace("|", "\\|"))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
