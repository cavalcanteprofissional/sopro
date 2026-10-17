"""Testes do pipeline em tempo real (sopro.app.realtime)."""

import array

from sopro.app.detection import DetectionService
from sopro.app.realtime import RealtimePipeline, default_frame
from sopro.core.audio.contracts import SOURCE_MIC, AudioSource
from sopro.core.glossary.package import load_package
from sopro.core.stt.provider import STTProvider, Transcript

SEED_PATH = "data/domains/tech-en-pt"


class FakeProvider(STTProvider):
    def __init__(self, text: str = "the transformer model is large") -> None:
        self.text = text

    def warmup(self) -> None:
        pass

    def transcribe(self, segment) -> Transcript:
        return Transcript(text=self.text, start_ms=0, end_ms=1000, source=segment.source)

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


def test_drain_flushes_pending_speech():
    pipeline = RealtimePipeline(_service())

    for chunk in _chunks(_tone(600)):
        assert pipeline.handle_frame(default_frame(chunk)) == []

    detections = pipeline.drain()

    assert [d.term for d in detections] == ["transformer"]


def test_run_reads_source_and_reports_detections():
    frames = [default_frame(c) for c in _chunks(_tone(500) + _silence(400))]
    source = FakeSource(frames)
    pipeline = RealtimePipeline(_service())
    seen = []

    pipeline.run(source, poll_timeout=0.0, should_stop=lambda: not source.frames, on_detection=seen.append)

    assert [d.term for d in seen] == ["transformer"]
