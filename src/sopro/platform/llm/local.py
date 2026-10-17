"""Provedor de LLM local via API compatível com chat (docs/02 §3.2, docs/05 A7).

Fala o subconjunto OpenAI ``/chat/completions`` — funciona com Ollama, LM Studio,
llama.cpp server e afins. Usa só a biblioteca padrão. O ``opener`` é injetável.
"""

from __future__ import annotations

import urllib.request

from sopro.platform.llm._http import Opener, chat_completion

DEFAULT_MODEL = "llama3.1"


class LocalLLMProvider:
    """Cliente de um servidor de chat local (OpenAI-compatible)."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str = DEFAULT_MODEL,
        api_key: str = "",
        timeout: float = 30.0,
        opener: Opener | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.name = f"local:{self.model}"
        self._api_key = api_key
        self._timeout = timeout
        self._opener: Opener = opener or urllib.request.urlopen

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        return chat_completion(
            opener=self._opener,
            base_url=self.base_url,
            payload=payload,
            api_key=self._api_key,
            timeout=self._timeout,
        )
