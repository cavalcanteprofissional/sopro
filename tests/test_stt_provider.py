"""Testes da interface STTProvider e do adapter local de Whisper."""

import pytest

from sopro.core.stt.local_whisper import LocalWhisperProvider
from sopro.core.stt.provider import (
    SAMPLE_RATE_HZ,
    AudioSegment,
    STTProvider,
    Transcript,
)


class FakeProvider(STTProvider):
    def __init__(self):
        self.calls = []

    def warmup(self):
        self.calls.append("warmup")

    def transcribe(self, segment):
        self.calls.append(("transcribe", segment.source))
        return Transcript(
            text=segment.vocabulary_hint[0] if segment.vocabulary_hint else "olá",
            start_ms=0,
            end_ms=1000,
            source=segment.source,
            confidence=0.9,
        )

    def close(self):
        self.calls.append("close")


def test_audio_segment_defaults():
    seg = AudioSegment(pcm=b"\x00\x00")
    assert seg.sample_rate == SAMPLE_RATE_HZ
    assert seg.source == "system"
    assert seg.language == "en"
    assert seg.vocabulary_hint == ()


def test_audio_segment_rejects_unknown_source():
    with pytest.raises(ValueError):
        AudioSegment(pcm=b"", source="speaker")


def test_audio_segment_rejects_bad_sample_rate():
    with pytest.raises(ValueError):
        AudioSegment(pcm=b"", sample_rate=0)


def test_fake_provider_satisfies_interface():
    provider: STTProvider = FakeProvider()
    provider.warmup()
    out = provider.transcribe(AudioSegment(pcm=b"\x01", source="mic", vocabulary_hint=("fairness",)))
    provider.close()

    assert isinstance(out, Transcript)
    assert out.text == "fairness"
    assert out.source == "mic"
    assert provider.calls == ["warmup", ("transcribe", "mic"), "close"]


def test_local_whisper_delegates_and_tracks_ready():
    recorded = {}

    def transcribe(segment):
        recorded["source"] = segment.source
        return Transcript(text="ok", start_ms=0, end_ms=500, source=segment.source)

    provider = LocalWhisperProvider("whisper-small-en", transcribe=transcribe)
    assert provider.model_id == "whisper-small-en"
    assert provider.ready is False

    provider.warmup()
    assert provider.ready is True

    out = provider.transcribe(AudioSegment(pcm=b"\x01"))
    assert out.text == "ok"
    assert recorded["source"] == "system"

    provider.close()
    assert provider.ready is False


def test_local_whisper_rejects_wrong_sample_rate():
    provider = LocalWhisperProvider("m", transcribe=lambda s: Transcript("", 0, 0))
    with pytest.raises(ValueError):
        provider.transcribe(AudioSegment(pcm=b"", sample_rate=8_000))


def test_local_whisper_requires_model_id():
    with pytest.raises(ValueError):
        LocalWhisperProvider("", transcribe=lambda s: Transcript("", 0, 0))
