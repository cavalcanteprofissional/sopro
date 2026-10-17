"""Testes do provedor STT da Groq e da seleção de provedor (docs/05 A8)."""

import json
import socket
import urllib.error

import pytest

from sopro.core.config import InMemorySecretStore, Settings
from sopro.core.stt import (
    AudioSegment,
    STTRateLimited,
    STTTimeout,
    STTUnavailable,
)
from sopro.platform.stt.factory import create_provider
from sopro.platform.stt.groq_stt import GroqSTTProvider

SECOND = 32000  # 16 kHz mono 16-bit => 32000 bytes por segundo


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _segment(seconds: int, source: str = "system", end_ms: int = 0) -> AudioSegment:
    return AudioSegment(
        pcm=b"\x00" * (SECOND * seconds),
        sample_rate=16000,
        source=source,
        language="en",
        vocabulary_hint=("transformer",),
    )


def test_groq_stt_buffers_until_minimum_duration():
    requests: list = []

    def opener(request, timeout=0):
        requests.append(request)
        return FakeResponse({"text": "the transformer model"})

    provider = GroqSTTProvider(
        api_key="secret", min_seconds=10.0, max_seconds=30.0, opener=opener
    )

    first = provider.transcribe(_segment(5))
    second = provider.transcribe(_segment(5))

    assert first.text == ""
    assert second.text == "the transformer model"
    assert len(requests) == 1
    body = requests[0].data
    assert b'name="file"' in body
    assert b"audio/wav" in body
    assert b"RIFF" in body
    assert body.count(b"transformer") == 1  # dica de vocabulário


def test_groq_stt_separates_buffers_by_source():
    calls = {"n": 0}

    def opener(request, timeout=0):
        calls["n"] += 1
        return FakeResponse({"text": "x"})

    provider = GroqSTTProvider(api_key="k", min_seconds=10.0, opener=opener)

    provider.transcribe(_segment(5, source="system"))
    provider.transcribe(_segment(5, source="mic"))  # buffer distinto, não completa
    assert calls["n"] == 0

    provider.transcribe(_segment(5, source="system"))
    assert calls["n"] == 1


def test_groq_stt_maps_rate_limit():
    def opener(request, timeout=0):
        raise urllib.error.HTTPError("u", 429, "too many", {}, None)

    provider = GroqSTTProvider(api_key="k", min_seconds=1.0, opener=opener)

    with pytest.raises(STTRateLimited):
        provider.transcribe(_segment(2))


def test_groq_stt_maps_timeout():
    def opener(request, timeout=0):
        raise socket.timeout("slow")

    provider = GroqSTTProvider(api_key="k", min_seconds=1.0, opener=opener)

    with pytest.raises(STTTimeout):
        provider.transcribe(_segment(2))


def test_groq_stt_requires_key():
    with pytest.raises(STTUnavailable):
        GroqSTTProvider(api_key="")


# -- fábrica -----------------------------------------------------------------


def test_create_provider_groq_without_key_raises():
    settings = Settings(stt_provider="groq")

    with pytest.raises(STTUnavailable):
        create_provider(settings, secret_store=InMemorySecretStore())


def test_create_provider_groq_with_key():
    store = InMemorySecretStore()
    store.set("groq_api_key", "secret")
    settings = Settings(stt_provider="groq")

    provider = create_provider(settings, secret_store=store)

    assert isinstance(provider, GroqSTTProvider)
    assert provider._model == settings.groq_stt_model
