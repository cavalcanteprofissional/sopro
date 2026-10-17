"""Adaptador do LLM para a cascata do :class:`SenseResolver` (docs/02 §3.4).

Implementa :class:`~sopro.core.rag.resolver.SenseChooser` sobre um
:class:`~sopro.core.llm.provider.LLMProvider`: monta o prompt B1 com as acepções
candidatas, chama o modelo e traduz ``chosen_sense_id`` de volta ao índice da
candidata. Falhas de rede/esquema viram ``None`` (o resolvedor mantém o vetor).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from sopro.core.glossary.package import Sense, Term
from sopro.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from sopro.core.llm.provider import LLMError, LLMProvider
from sopro.core.llm.schema import LLMSchemaError, parse_entry_json

log = logging.getLogger(__name__)


class LLMSenseChooser:
    """Escolhe, via LLM, uma das acepções candidatas de um termo ambíguo."""

    def __init__(
        self,
        provider: LLMProvider,
        *,
        domain: str = "",
        output_lang: str = "pt-BR",
    ) -> None:
        self._provider = provider
        self._domain = domain
        self._output_lang = output_lang

    def choose(
        self, term: Term, context: str, candidates: Sequence[Sense]
    ) -> int | None:
        if not candidates:
            return None
        payload = [
            {
                "sense_id": str(sense.ordinal),
                "translation": sense.translation_pt,
                "definition": sense.definition_pt,
                "domain_tag": sense.domain_tag,
            }
            for sense in candidates
        ]
        user = build_user_prompt(
            domain=self._domain,
            output_lang=self._output_lang,
            term=term.canonical_en,
            context=context,
            candidates=payload,
        )
        try:
            raw = self._provider.complete(SYSTEM_PROMPT, user)
            result = parse_entry_json(raw, model=self._provider.name)
        except (LLMError, LLMSchemaError) as exc:
            log.warning("LLM não decidiu a acepção de %r: %s", term.canonical_en, exc)
            return None
        if result.chosen_sense_id is None:
            return None
        try:
            chosen = int(result.chosen_sense_id)
        except ValueError:
            return None
        for index, sense in enumerate(candidates):
            if sense.ordinal == chosen:
                return index
        return None
