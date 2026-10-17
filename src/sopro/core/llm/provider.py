"""Interface de provedor de LLM (docs/02 §3.2).

O LLM é a **exceção**: só entra para desambiguar (abaixo do limiar) ou para termos
fora do glossário. O provedor é deliberadamente de baixo nível — recebe o prompt de
sistema e o de usuário e devolve o texto (esperado como JSON). A construção do
prompt e a validação do JSON ficam em :mod:`sopro.core.llm.prompts` e
:mod:`sopro.core.llm.schema`, mantendo o provedor trocável (local, Groq, fake).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Falha ao consultar o provedor de LLM (rede, limite, resposta inválida)."""


@runtime_checkable
class LLMProvider(Protocol):
    """Provedor de LLM capaz de completar um par de mensagens."""

    name: str

    def complete(self, system: str, user: str) -> str:
        """Devolve a resposta bruta do modelo para o par de mensagens."""
        ...
