"""Testes do hotword por STT curto alimentado pelo pipeline de áudio."""

from __future__ import annotations

import time

from sopro.core.hotword.backends.stt_fallback import SttShortHotwordDetector
from sopro.core.stt import AudioSegment, Transcript


class FakeProvider:
    def __init__(self, text="sopro"):
        self.text = text
        self.segments = []

    def warmup(self):
        return None

    def transcribe(self, segment: AudioSegment) -> Transcript:
        self.segments.append(segment)
        return Transcript(text=self.text, start_ms=0, end_ms=500, confidence=0.9)

    def close(self):
        return None


def _loud_frame() -> bytes:
    return b"\x00\x30" * 480


def _silence_frame() -> bytes:
    return b"\x00\x00" * 480


def _utterance(detector) -> None:
    for _ in range(20):
        detector.feed(_loud_frame())
    for _ in range(16):
        detector.feed(_silence_frame())


def test_feed_triggers_callback_and_debounces():
    provider = FakeProvider()
    detector = SttShortHotwordDetector(
        phrase="sopro",
        provider_factory=lambda: provider,
    )
    calls = []
    detector.register_callback(lambda: calls.append(True))
    detector.start()
    _utterance(detector)
    deadline = time.monotonic() + 3
    while not calls and time.monotonic() < deadline:
        time.sleep(0.02)
    assert calls == [True]
    assert provider.segments

    _utterance(detector)
    time.sleep(0.3)
    assert calls == [True]
    detector.stop()


def test_feed_ignores_other_words():
    provider = FakeProvider(text="outra palavra")
    detector = SttShortHotwordDetector(
        phrase="sopro",
        provider_factory=lambda: provider,
    )
    calls = []
    detector.register_callback(lambda: calls.append(True))
    detector.start()
    _utterance(detector)
    time.sleep(0.5)
    detector.stop()
    assert calls == []


def test_detector_does_not_import_sounddevice():
    import sys

    SttShortHotwordDetector(phrase="sopro")
    assert "sounddevice" not in sys.modules
