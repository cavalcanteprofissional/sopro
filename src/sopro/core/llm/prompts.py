"""Prompts do LLM (docs/05 B1): definição e escolha de acepção em JSON."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

SYSTEM_PROMPT = """\
Você é um assistente de glossário técnico. Responda SOMENTE com JSON válido, sem texto
extra e sem blocos de código.

Tarefa: dado um termo em inglês ouvido em uma aula, o domínio ativo, o idioma de saída e
o contexto recente, escolha o significado correto para o domínio e gere uma explicação curta.

Esquema:
{
  "term": string,
  "in_glossary": boolean,
  "chosen_sense_id": string | null,
  "translation": string,
  "definition": string,
  "confidence": number,
  "generated": boolean
}

Regras:
- Use apenas as acepções fornecidas quando houver; escolha a mais coerente com o domínio
  e o contexto.
- Se o termo não estiver no glossário, gere definição curta e marque generated=true.
- Se não tiver certeza, use confidence baixa; NÃO invente fatos, siglas ou fontes.
- Não repita o contexto; não adicione opiniões; mantenha tom neutro."""


def build_user_prompt(
    *,
    domain: str,
    output_lang: str,
    term: str,
    context: str,
    candidates: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Monta o prompt de usuário do B1 com as acepções candidatas (ou vazio)."""
    payload = json.dumps(list(candidates), ensure_ascii=False)
    return (
        f"domínio: {domain}\n"
        f"idioma_de_saída: {output_lang}\n"
        f"termo_ouvido: {term}\n"
        f'contexto_recente: """{context}"""\n'
        f"acepcoes_candidatas: {payload}"
    )
