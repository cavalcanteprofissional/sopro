"""Caminho de termo fora do glossário: gera, guarda em cache e enfileira (docs/05 A7).

Quando o termo não está no glossário, consulta o :class:`LLMProvider` com o prompt
B1 (sem candidatas), valida o JSON e grava a entrada em ``generated_entry`` —
separada de ``term``/``sense`` até o usuário aprovar (docs/02 §6). O cache evita
reconsultar o mesmo termo; o resultado é sempre marcado ``generated=True``.
"""

from __future__ import annotations

import logging

from sopro.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from sopro.core.llm.provider import LLMError, LLMProvider
from sopro.core.llm.schema import EntryResult, LLMSchemaError, parse_entry_json
from sopro.core.repo import GeneratedEntryRecord, Repository

log = logging.getLogger(__name__)


class GeneratedEntryService:
    """Gera explicações para termos novos e mantém a fila de aprovação."""

    def __init__(
        self,
        provider: LLMProvider,
        repo: Repository,
        *,
        domain: str = "",
        output_lang: str = "pt-BR",
        use_cache: bool = True,
    ) -> None:
        self._provider = provider
        self._repo = repo
        self._domain = domain
        self._output_lang = output_lang
        self._use_cache = use_cache

    def explain(self, term: str, context: str = "") -> EntryResult | None:
        """Devolve a definição gerada para ``term`` (cache primeiro); ``None`` em falha."""
        term = term.strip()
        if not term:
            return None
        if self._use_cache:
            cached = self._repo.get_generated_entry(term, model=self._provider.name)
            if cached is not None:
                return _to_result(cached, self._provider.name)
        user = build_user_prompt(
            domain=self._domain,
            output_lang=self._output_lang,
            term=term,
            context=context,
            candidates=(),
        )
        try:
            raw = self._provider.complete(SYSTEM_PROMPT, user)
            result = parse_entry_json(raw, model=self._provider.name)
        except (LLMError, LLMSchemaError) as exc:
            log.warning("LLM falhou ao explicar %r: %s", term, exc)
            return None
        result = EntryResult(
            term=term,
            translation=result.translation,
            definition=result.definition,
            confidence=result.confidence,
            in_glossary=False,
            generated=True,
            chosen_sense_id=None,
            model=self._provider.name,
        )
        self._repo.add_generated_entry(
            term,
            result.definition,
            self._provider.name,
            translation=result.translation,
            confidence=result.confidence,
        )
        return result

    def pending(self) -> list[GeneratedEntryRecord]:
        """Entradas geradas ainda não aprovadas (fila de revisão)."""
        return self._repo.list_generated_entries(approved=False)

    def approve(self, entry_id: int) -> None:
        self._repo.approve_generated_entry(entry_id)


def _to_result(record: GeneratedEntryRecord, model: str) -> EntryResult:
    return EntryResult(
        term=record.term,
        translation=record.translation,
        definition=record.definition,
        confidence=record.confidence,
        in_glossary=False,
        generated=True,
        chosen_sense_id=None,
        model=model,
    )
