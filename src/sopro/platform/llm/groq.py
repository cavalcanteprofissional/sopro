"""Provedor de LLM opcional via Groq (docs/05 A8).

Cliente OpenAI-compatível hospedado. Respeita o plano gratuito com **backoff** em
``429`` (usando ``Retry-After`` quando presente) e retorna erro tipado em vez de
derrubar o pipeline (o orquestrador cai para o provedor local). A chave vem do
cofre do SO e **nunca** é registrada em log.
"""

from __future__ import annotations

import time
import urllib.request

from sopro.core.llm.provider import LLMError
from sopro.platform.llm._http import HTTPStatusError, Opener, chat_completion

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.1-8b-instant"


class GroqLLMProvider:
    """Cliente do Groq com retry exponencial em limite de taxa."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = GROQ_BASE_URL,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 20.0,
        opener: Opener | None = None,
        sleep=time.sleep,
    ) -> None:
        if not api_key:
            raise LLMError("chave do Groq ausente")
        self.base_url = base_url.rstrip("/")
        self.model = model or DEFAULT_MODEL
        self.name = f"groq:{self.model}"
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max(int(max_retries), 0)
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._opener: Opener = opener or urllib.request.urlopen
        self._sleep = sleep

    def complete(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        delay = self._base_delay
        for attempt in range(self._max_retries + 1):
            try:
                return chat_completion(
                    opener=self._opener,
                    base_url=self.base_url,
                    payload=payload,
                    api_key=self._api_key,
                    timeout=self._timeout,
                )
            except HTTPStatusError as exc:
                if exc.status != 429 or attempt >= self._max_retries:
                    raise
                wait = exc.retry_after if exc.retry_after is not None else delay
                self._sleep(min(wait, self._max_delay))
                delay = min(delay * 2, self._max_delay)
        raise LLMError("Groq: tentativas esgotadas")
