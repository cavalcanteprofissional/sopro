"""Chamada HTTP compartilhada a APIs de chat OpenAI-compatíveis (stdlib apenas).

Usado pelos provedores ``local`` e ``groq``. Trata erros de rede/HTTP como
:class:`LLMError` e extrai o texto de ``choices[0].message.content``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from sopro.core.llm.provider import LLMError

Opener = Callable[..., Any]


class HTTPStatusError(LLMError):
    """Erro HTTP do provedor, com o código de status e ``Retry-After`` opcional."""

    def __init__(
        self, status: int, message: str, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None


def chat_completion(
    *,
    opener: Opener,
    base_url: str,
    payload: dict,
    api_key: str = "",
    timeout: float = 30.0,
) -> str:
    """POST ``/chat/completions`` e devolve o conteúdo textual da resposta."""
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if api_key:
        request.add_header("Authorization", f"Bearer {api_key}")
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read()
    except HTTPStatusError:
        raise
    except urllib.error.HTTPError as exc:
        headers = exc.headers
        retry_after = _parse_retry_after(headers.get("Retry-After") if headers else None)
        raise HTTPStatusError(
            exc.code, f"HTTP {exc.code} do LLM", retry_after=retry_after
        ) from exc
    except Exception as exc:  # noqa: BLE001 - rede viram LLMError
        raise LLMError(f"falha ao consultar o LLM: {exc}") from exc
    return _extract_content(body)


def _extract_content(body: bytes) -> str:
    try:
        data = json.loads(body)
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"resposta inesperada do LLM: {exc}") from exc
    if not isinstance(content, str):
        raise LLMError("conteúdo do LLM não é texto")
    return content
