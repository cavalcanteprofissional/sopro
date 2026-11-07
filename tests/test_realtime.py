"""Testes do pipeline em tempo real (sopro.app.realtime)."""

import array

from sopro.app.detection import DetectionService
from sopro.app.realtime import RealtimePipeline, default_frame
from sopro.core.audio.contracts import SOURCE_MIC, AudioSource
from sopro.core.glossary.package import load_package
from sopro.core.stt.provider import STTProvider, Transcript

SEED_PATH = "data/domains/tech-en-pt"


class FakeProvider(STTProvider):
    def __init__(
        self,
        text: str = "the transformer model is large",
        by_source: dict[str, str] | None = None,
    ) -> None:
        self.text = text
        self.by_source = by_source or {}

    def warmup(self) -> None:
        pass

    def transcribe(self, segment) -> Transcript:
        text = self.by_source.get(segment.source, self.text)
        return Transcript(text=text, start_ms=0, end_ms=1000, source=segment.source)

    def close(self) -> None:
        pass


class FakeSource(AudioSource):
    def __init__(self, frames) -> None:
        self.frames = list(frames)
        self.started = False
        self.closed = False

    def list_devices(self):
        return []

    def start(self, config) -> None:
        self.started = True

    def read(self, timeout=None):
        return self.frames.pop(0) if self.frames else None

    def close(self) -> None:
        self.closed = True


def _tone(ms: int, rate: int = 16000, freq: int = 440, amp: int = 8000) -> bytes:
    samples = array.array("h")
    total = rate * ms // 1000
    period = max(2, rate // freq)
    for i in range(total):
        samples.append(amp if (i % period) < (period // 2) else -amp)
    return samples.tobytes()


def _silence(ms: int, rate: int = 16000) -> bytes:
    return bytes(rate * ms // 1000 * 2)


def _chunks(pcm: bytes, chunk_ms: int = 30, rate: int = 16000):
    size = rate * chunk_ms // 1000 * 2
    for i in range(0, len(pcm), size):
        yield pcm[i : i + size]


def _service() -> DetectionService:
    return DetectionService(FakeProvider(), load_package(SEED_PATH))


def test_handle_frame_detects_after_silence():
    pipeline = RealtimePipeline(_service())

    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk)))

    assert [d.term for d in detections] == ["transformer"]
    assert detections[0].source == "system"


def test_sources_have_separate_segmenters():
    pipeline = RealtimePipeline(_service())

    # fala do microfone ainda em andamento (sem silêncio): nada é emitido
    mic = []
    for chunk in _chunks(_tone(500)):
        mic.extend(pipeline.handle_frame(default_frame(chunk, source=SOURCE_MIC)))
    assert mic == []

    # o sistema não é afetado pelos quadros do microfone
    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk, source="system")))

    assert [d.term for d in detections] == ["transformer"]
    assert detections[0].source == "system"


def test_inactive_source_reports_level_without_detecting():
    levels = []
    pipeline = RealtimePipeline(
        _service(),
        on_source_level=lambda source, level, speaking: levels.append(
            (source, level, speaking)
        ),
    )
    pipeline.set_source_active(SOURCE_MIC, False)

    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk, source=SOURCE_MIC)))

    assert detections == []
    assert levels and all(source == SOURCE_MIC for source, _l, _s in levels)

    pipeline.set_source_active(SOURCE_MIC, True)
    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk, source=SOURCE_MIC)))

    assert [d.term for d in detections] == ["transformer"]
    assert detections[0].source == SOURCE_MIC


def test_mic_wins_arbitration_against_pending_system():
    now = [0.0]
    pipeline = RealtimePipeline(
        _service(), arbitration_ms=500, clock=lambda: now[0]
    )
    pipeline.set_source_active(SOURCE_MIC, True)

    for chunk in _chunks(_tone(500) + _silence(400)):
        assert pipeline.handle_frame(default_frame(chunk, source="system")) == []

    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk, source=SOURCE_MIC)))

    assert [(d.term, d.source) for d in detections] == [("transformer", SOURCE_MIC)]
    assert pipeline.flush_pending(now=1.0) == []


def test_different_system_content_still_commits_after_mic():
    now = [0.0]
    provider = FakeProvider(
        by_source={
            "system": "the transformer model is large",
            SOURCE_MIC: "the api returns data",
        }
    )
    pipeline = RealtimePipeline(
        DetectionService(provider, load_package(SEED_PATH)),
        arbitration_ms=500,
        clock=lambda: now[0],
    )
    pipeline.set_source_active(SOURCE_MIC, True)

    for chunk in _chunks(_tone(500) + _silence(400)):
        pipeline.handle_frame(default_frame(chunk, source="system"))

    detections = []
    for chunk in _chunks(_tone(500) + _silence(400)):
        detections.extend(pipeline.handle_frame(default_frame(chunk, source=SOURCE_MIC)))

    assert {(d.term, d.source) for d in detections} == {
        ("transformer", "system"),
        ("API", SOURCE_MIC),
    }


def test_system_commits_after_arbitration_timeout():
    now = [0.0]
    pipeline = RealtimePipeline(
        _service(), arbitration_ms=500, clock=lambda: now[0]
    )
    pipeline.set_source_active(SOURCE_MIC, True)

    for chunk in _chunks(_tone(500) + _silence(400)):
        assert pipeline.handle_frame(default_frame(chunk, source="system")) == []

    detections = pipeline.flush_pending(now=0.6)

    assert [(d.term, d.source) for d in detections] == [("transformer", "system")]


def test_drain_flushes_pending_speech():
    pipeline = RealtimePipeline(_service())

    for chunk in _chunks(_tone(600)):
        assert pipeline.handle_frame(default_frame(chunk)) == []

    detections = pipeline.drain()

    assert [d.term for d in detections] == ["transformer"]


def test_run_keeps_frames_while_slow_stt_processes():
    import time

    class SlowProvider(FakeProvider):
        def __init__(self):
            super().__init__()
            self.texts = iter(
                ["the transformer model is large", "ai is changing how we work"]
            )

        def transcribe(self, segment):
            time.sleep(0.05)
            return Transcript(
                text=next(self.texts),
                start_ms=0,
                end_ms=1000,
                source=segment.source,
            )

    pipeline = RealtimePipeline(
        DetectionService(SlowProvider(), load_package(SEED_PATH))
    )
    pcm = _tone(500) + _silence(400) + _tone(500) + _silence(400)
    source = FakeSource([default_frame(c) for c in _chunks(pcm)])
    seen = []

    pipeline.run(
        source,
        poll_timeout=0.0,
        should_stop=lambda: not source.frames,
        on_detection=seen.append,
        queue_size=4,
    )

    assert [d.term for d in seen] == ["transformer", "AI"]


def test_run_reads_source_and_reports_detections():
    frames = [default_frame(c) for c in _chunks(_tone(500) + _silence(400))]
    source = FakeSource(frames)
    pipeline = RealtimePipeline(_service())
    seen = []

    pipeline.run(
        source,
        poll_timeout=0.0,
        should_stop=lambda: not source.frames,
        on_detection=seen.append,
    )

    assert [d.term for d in seen] == ["transformer"]
