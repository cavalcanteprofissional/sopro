"""Testes do binding faster-whisper (com engine simulada, sem a dependência)."""

import math

import pytest

from sopro.core.stt import LocalWhisperProvider, STTUnavailable
from sopro.platform.stt import faster_whisper_engine as engine


class FakeChunk:
    def __init__(
        self,
        text: str,
        avg_logprob: float | None = None,
        no_speech_prob: float | None = None,
    ) -> None:
        self.text = text
        self.avg_logprob = avg_logprob
        self.no_speech_prob = no_speech_prob


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
    assert transcript.confidence is None


def test_transcribe_combines_logprob_and_no_speech_confidence(monkeypatch, fake_engine):
    class ScoredModel:
        def transcribe(self, audio, **kwargs):
            return [
                FakeChunk("hello", avg_logprob=-0.1, no_speech_prob=0.1),
                FakeChunk("world", avg_logprob=-0.2, no_speech_prob=0.2),
            ], object()

    monkeypatch.setattr(
        engine, "_load_model", lambda path, device, compute_type: ScoredModel()
    )
    provider = engine.build_provider("caminho")

    transcript = provider.transcribe(_segment(b"\x00\x00" * 160))

    expected = round(
        (math.exp(-0.1) + math.exp(-0.2)) / 2 * (1 - (0.1 + 0.2) / 2), 4
    )
    assert transcript.confidence == expected


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


def test_segment_vocabulary_hint_overrides_provider(fake_engine):
    provider = engine.build_provider("caminho", vocabulary_hint=("padrao",))

    provider.transcribe(_segment(b"\x00\x00" * 160, vocabulary_hint=("token", "bias")))

    _audio, kwargs = fake_engine.calls[0]
    assert kwargs["initial_prompt"] == "token, bias"


def test_transcribe_uses_greedy_temperature(fake_engine):
    provider = engine.build_provider("caminho")

    provider.transcribe(_segment(b"\x00\x00" * 160))

    _audio, kwargs = fake_engine.calls[0]
    assert kwargs["temperature"] == 0.0


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


def _segment(pcm: bytes, vocabulary_hint=()):
    from sopro.core.stt import AudioSegment

    return AudioSegment(pcm=pcm, vocabulary_hint=vocabulary_hint)
