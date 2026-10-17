"""Testes do modo demonstração (sopro.app.demo)."""

from sopro.app.demo import (
    DEMO_TRANSCRIPTS,
    DemoAudioSource,
    DemoProvider,
    build_demo_pcm,
)
from sopro.core.audio import SOURCE_SYSTEM
from sopro.core.stt import AudioSegment

SEED_PATH = "data/domains/tech-en-pt"


def test_demo_provider_cycles_transcripts():
    provider = DemoProvider(("one", "two"))
    first = provider.transcribe(AudioSegment(pcm=b"\x00\x00"))
    second = provider.transcribe(AudioSegment(pcm=b"\x00\x00"))
    third = provider.transcribe(AudioSegment(pcm=b"\x00\x00"))

    assert (first.text, second.text, third.text) == ("one", "two", "one")
    assert first.source == SOURCE_SYSTEM
    assert provider.calls == 3


def test_demo_provider_defaults():
    provider = DemoProvider()
    transcript = provider.transcribe(AudioSegment(pcm=b"\x00\x00"))
    assert transcript.text == DEMO_TRANSCRIPTS[0]


def test_build_demo_pcm_has_speech_and_silence():
    pcm = build_demo_pcm(rate=16000, speech_ms=100, silence_ms=100)
    assert len(pcm) == (100 + 100) * 16000 // 1000 * 2
    assert any(pcm)  # há amostras não nulas (fala)


def test_demo_audio_source_yields_frames_and_cycles():
    source = DemoAudioSource(rate=16000, frame_ms=30)
    source.start(None)
    frames = [source.read() for _ in range(5)]
    assert all(frame.source == SOURCE_SYSTEM for frame in frames)
    assert all(frame.sample_rate == 16000 for frame in frames)
    assert all(len(frame.pcm) % 2 == 0 for frame in frames)

    total = len(source._frames)
    first = source._frames[0]
    again = [source.read() for _ in range(total)]
    assert any(frame.pcm == first for frame in again)


def test_demo_pipeline_produces_detections():
    from sopro.app.detection import DetectionService
    from sopro.app.realtime import RealtimePipeline
    from sopro.core.glossary.package import load_package

    provider = DemoProvider()
    package = load_package(SEED_PATH)
    pipeline = RealtimePipeline(DetectionService(provider, package))
    source = DemoAudioSource()
    source.start(None)

    detected = []
    for _ in range(600):
        frame = source.read()
        if frame is None:
            break
        detected.extend(pipeline.handle_frame(frame))

    assert detected
    assert any(d.term for d in detected)
