"""Testes do cofre de segredos (sopro.core.config.secrets)."""

import builtins

import pytest

from sopro.core.config.secrets import (
    InMemorySecretStore,
    KeyringSecretStore,
    SecretError,
)


def test_in_memory_store_get_set_delete():
    store = InMemorySecretStore()

    assert store.get("groq") is None
    store.set("groq", "chave-123")
    assert store.get("groq") == "chave-123"
    store.delete("groq")
    assert store.get("groq") is None


def test_in_memory_delete_missing_is_noop():
    store = InMemorySecretStore()

    store.delete("inexistente")


def test_keyring_store_raises_when_keyring_missing(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "keyring":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    store = KeyringSecretStore()

    with pytest.raises(SecretError):
        store.get("groq")
