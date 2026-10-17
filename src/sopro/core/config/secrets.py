"""Armazenamento de segredos (chaves de API) fora do banco (docs/05 A6, docs/02 §10).

Aspira usar o cofre de credenciais do SO. ``keyring`` é opcional: quando ausente,
``KeyringSecretStore`` avisa em vez de gravar segredos em texto puro. Nada aqui
escreve em logs.
"""

from __future__ import annotations

from typing import Protocol

DEFAULT_SERVICE = "sopro"
GROQ_API_KEY = "groq_api_key"


class SecretError(Exception):
    """Falha ao acessar o armazenamento de segredos."""


class SecretStore(Protocol):
    """Contrato de um cofre de segredos por chave."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def delete(self, key: str) -> None: ...


class InMemorySecretStore:
    """Cofre em memória (testes e execuções efêmeras). Não persiste."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._values.get(key)

    def set(self, key: str, value: str) -> None:
        self._values[key] = value

    def delete(self, key: str) -> None:
        self._values.pop(key, None)


class KeyringSecretStore:
    """Cofre do SO via ``keyring`` (opcional), se disponível."""

    def __init__(self, service: str = DEFAULT_SERVICE) -> None:
        self._service = service

    def _keyring(self):
        try:
            import keyring  # type: ignore
        except ImportError as exc:  # pragma: no cover - depende do ambiente
            raise SecretError(
                "keyring não está instalado; instale o extra de credenciais ou use "
                "InMemorySecretStore"
            ) from exc
        return keyring

    def get(self, key: str) -> str | None:
        return self._keyring().get_password(self._service, key)

    def set(self, key: str, value: str) -> None:
        self._keyring().set_password(self._service, key, value)

    def delete(self, key: str) -> None:
        try:
            self._keyring().delete_password(self._service, key)
        except Exception:  # noqa: BLE001 - chave inexistente varia por backend
            pass
