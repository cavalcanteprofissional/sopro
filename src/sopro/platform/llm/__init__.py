"""Fábrica de provedores de LLM (docs/02 §3.2).

Liga a preferência ``llm_provider`` (``off``/``local``/``groq``) a um
:class:`~sopro.core.llm.provider.LLMProvider`. ``off`` devolve ``None``; ``groq``
vive em :mod:`sopro.platform.llm.groq` (importado sob demanda). Nunca grava segredos
em log; a chave vem do cofre do SO (``core.config.secrets``).
"""

from __future__ import annotations

from sopro.core.config import Settings
from sopro.core.llm.provider import LLMError, LLMProvider
from sopro.platform.llm.local import LocalLLMProvider

GROQ_SECRET_KEY = "groq_api_key"


def create_provider(settings: Settings, secret_store=None) -> LLMProvider | None:
    """Monta o provedor conforme as configurações; ``None`` quando desligado."""
    name = settings.llm_provider
    if name == "off":
        return None
    if name == "local":
        return LocalLLMProvider(
            base_url=settings.llm_base_url, model=settings.llm_model
        )
    if name == "groq":
        from sopro.platform.llm.groq import GroqLLMProvider

        api_key = secret_store.get(GROQ_SECRET_KEY) if secret_store else None
        if not api_key:
            raise LLMError(
                "chave do Groq ausente; salve-a no cofre antes de usar o provedor Groq"
            )
        return GroqLLMProvider(
            api_key=api_key, model=settings.llm_model or "llama-3.1-8b-instant"
        )
    raise LLMError(f"provedor de LLM desconhecido: {name!r}")
