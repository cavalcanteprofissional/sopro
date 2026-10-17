"""Validação da saída JSON do LLM (prompt B1, docs/05).

O modelo deve responder **somente** com um objeto JSON. Para tolerar variações
comuns (blocos de código, texto antes/depois), :func:`extract_json` recorta o
primeiro objeto balanceado; :func:`parse_entry_json` valida o esquema e devolve um
:class:`EntryResult` imutável.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

MAX_DEFINITION_CHARS = 400


class LLMSchemaError(Exception):
    """A resposta do LLM não é um objeto JSON válido conforme o esquema."""


@dataclass(frozen=True)
class EntryResult:
    """Saída validada do LLM para um termo (esquema do prompt B1)."""

    term: str
    translation: str
    definition: str
    confidence: float
    in_glossary: bool
    generated: bool
    chosen_sense_id: str | None = None
    model: str = ""


def extract_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON balanceado do texto do modelo."""
    start = text.find("{")
    if start == -1:
        raise LLMSchemaError("resposta sem objeto JSON")
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start : index + 1]
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError as exc:
                    raise LLMSchemaError(f"JSON inválido: {exc}") from exc
                if not isinstance(data, dict):
                    raise LLMSchemaError("resposta JSON não é um objeto")
                return data
    raise LLMSchemaError("objeto JSON não fechado na resposta")


def _string(data: dict, key: str, default: str = "") -> str:
    value = data.get(key, default)
    if value is None:
        return default
    return str(value)


def _bool(data: dict, key: str, default: bool = False) -> bool:
    value = data.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "sim", "yes")
    return bool(value)


def _confidence(data: dict) -> float:
    value = data.get("confidence", 0.0)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(number, 0.0), 1.0)


def parse_entry_json(text: str, *, model: str = "") -> EntryResult:
    """Valida a resposta do LLM e devolve um :class:`EntryResult`."""
    data = extract_json(text)
    term = _string(data, "term").strip()
    if not term:
        raise LLMSchemaError("campo 'term' ausente ou vazio")
    definition = _string(data, "definition").strip()[:MAX_DEFINITION_CHARS]
    chosen = data.get("chosen_sense_id")
    return EntryResult(
        term=term,
        translation=_string(data, "translation").strip(),
        definition=definition,
        confidence=_confidence(data),
        in_glossary=_bool(data, "in_glossary"),
        generated=_bool(data, "generated"),
        chosen_sense_id=None if chosen is None else str(chosen),
        model=model,
    )
