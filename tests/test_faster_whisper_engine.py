"""Testes do binding faster-whisper (com engine simulada, sem a dependência)."""

import pytest

from sopro.core.stt import LocalWhisperProvider, STTUnavailable
from sopro.platform.stt import faster_whisper_engine as engine


class FakeChunk:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeModel:
    def __init__(self) -> None:
        self.calls = []

    def transcribe(self, audio, **kwargs):
        self.calls.append((audio, kwargs))
        return [FakeChunk("hello"), FakeChunk("world")], object()


@pytest.fixture
def fake_engine(monkeypatch):
    model = FakeModel()
    monkeypatch.setattr(engine, "_load_model", lambda path, device, compute_type: model)
    monkeypatch.setattr(engine, "_to_audio", lambda pcm: pcm)
    return model


def test_build_provider_returns_local_provider(fake_engine):
    provider = engine.build_provider("caminho", model_id="m1")

    assert isinstance(provider, LocalWhisperProvider)
    assert provider.model_id == "m1"
    assert provider.ready is False


def test_warmup_loads_model_once(fake_engine, monkeypatch):
    calls = []
    monkeypatch.setattr(
        engine, "_load_model", lambda path, device, compute_type: calls.append(1) or fake_engine
    )
    provider = engine.build_provider("caminho")

    provider.warmup()
    provider.warmup()

    assert provider.ready is True
    assert len(calls) == 1


def test_transcribe_joins_text_and_sets_timing(fake_engine):
    provider = engine.build_provider("caminho")
    pcm = b"\x00\x00" * 8000

    transcript = provider.transcribe(_segment(pcm))

    assert transcript.text == "hello world"
    assert transcript.start_ms == 0
    assert transcript.end_ms == 500
    assert transcript.source == "system"


def test_transcribe_passes_language_and_prompt(fake_engine):
    provider = engine.build_provider("caminho", language="en", vocabulary_hint=("RAG", "bias"))

    provider.transcribe(_segment(b"\x00\x00" * 160))

    audio, kwargs = fake_engine.calls[0]
    assert kwargs["language"] == "en"
    assert kwargs["initial_prompt"] == "RAG, bias"
    assert kwargs["vad_filter"] is False


def test_no_vocabulary_hint_sends_none_prompt(fake_engine):
    provider = engine.build_provider("caminho")

    provider.transcribe(_segment(b"\x00\x00" * 160))

    _audio, kwargs = fake_engine.calls[0]
    assert kwargs["initial_prompt"] is None


def test_close_forces_reload(fake_engine, monkeypatch):
    calls = []
    monkeypatch.setattr(
        engine, "_load_model", lambda path, device, compute_type: calls.append(1) or fake_engine
    )
    provider = engine.build_provider("caminho")

    provider.transcribe(_segment(b"\x00\x00" * 160))
    provider.close()
    provider.transcribe(_segment(b"\x00\x00" * 160))

    assert len(calls) == 2


def test_load_model_missing_dependency_raises(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("no module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(STTUnavailable):
        engine._load_model("x", "cpu", "int8")


def _segment(pcm: bytes):
    from sopro.core.stt import AudioSegment

    return AudioSegment(pcm=pcm)
