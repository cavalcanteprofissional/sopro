"""Camada de LLM (docs/02 §3.2): exceção para desambiguação e termos fora do glossário.

O LLM **não** participa de toda frase. Este pacote expõe:

- :class:`LLMProvider` — contrato de baixo nível (``complete(system, user)``);
- promps e validação do JSON do prompt B1 (``prompts``, ``schema``);
- :class:`LLMSenseChooser` — adapta o LLM ao passo ``llm`` do ``SenseResolver``;
- :class:`GeneratedEntryService` — termos fora do glossário, com cache e aprovação.
"""

from __future__ import annotations

from sopro.core.llm.candidates import (
    COMMON_WORDS,
    Candidate,
    RateLimiter,
    extract_candidates,
)
from sopro.core.llm.chooser import LLMSenseChooser
from sopro.core.llm.generate import GeneratedEntryService
from sopro.core.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from sopro.core.llm.provider import LLMError, LLMProvider
from sopro.core.llm.schema import (
    EntryResult,
    LLMSchemaError,
    extract_json,
    parse_entry_json,
)

__all__ = [
    "COMMON_WORDS",
    "Candidate",
    "EntryResult",
    "GeneratedEntryService",
    "LLMError",
    "LLMProvider",
    "LLMSchemaError",
    "LLMSenseChooser",
    "RateLimiter",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "extract_candidates",
    "extract_json",
    "parse_entry_json",
]
