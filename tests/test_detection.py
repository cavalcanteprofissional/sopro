"""Testes do serviço de detecção (sopro.app.detection)."""

import array

import pytest

from sopro.app.detection import Detection, DetectionService
from sopro.core.glossary.package import load_package
from sopro.core.repo import Database, Repository, import_package
from sopro.core.stt.provider import STTProvider, Transcript
from sopro.core.vad import SpeechSegment
from sopro.platform.popup import PopupQueue

SEED_PATH = "data/domains/tech-en-pt"


class FakeProvider(STTProvider):
    def __init__(self, text: str, confidence: float | None = None) -> None:
        self.text = text
        self.confidence = confidence
        self.calls = 0

    def warmup(self) -> None:
        pass

    def transcribe(self, segment) -> Transcript:
        self.calls += 1
        return Transcript(
            text=self.text,
            start_ms=0,
            end_ms=1000,
            source=segment.source,
            confidence=self.confidence,
        )

    def close(self) -> None:
        pass


def _speech() -> SpeechSegment:
    return SpeechSegment(start_ms=0, end_ms=1000, pcm=b"\x00" * 3200)


def _tone_pcm(duration_ms: int, rate: int = 16000, freq: int = 440, amp: int = 8000) -> bytes:
    samples = array.array("h")
    total = rate * duration_ms // 1000
    period = rate // freq
    for i in range(total):
        samples.append(amp if (i % period) < (period // 2) else -amp)
    return samples.tobytes()


def _service(provider, **kwargs) -> DetectionService:
    package = load_package(SEED_PATH)
    return DetectionService(provider, package, **kwargs)


def test_process_detects_known_term():
    provider = FakeProvider("the transformer model is large")

    detections = _service(provider).process(_speech())

    assert [d.term for d in detections] == ["transformer"]
    assert detections[0].translation  # tradução vinda do glossário
    assert provider.calls == 1


def test_process_ignores_unknown_text():
    provider = FakeProvider("nothing to see here")

    assert _service(provider).process(_speech()) == []


def test_process_ignores_low_confidence_transcript():
    provider = FakeProvider("the transformer model", confidence=0.1)

    assert _service(provider).process(_speech()) == []


def test_process_accepts_transcript_at_min_confidence():
    provider = FakeProvider("the transformer model", confidence=0.2)

    detections = _service(provider, min_confidence=0.2).process(_speech())

    assert [d.term for d in detections] == ["transformer"]


def test_process_offers_popup():
    provider = FakeProvider("the transformer model")
    popup = PopupQueue()

    detections = _service(provider, popup=popup).process(_speech())

    assert popup.is_active("transformer")
    assert popup.active_items()[0].payload is detections[0]


def test_process_persists_detection():
    provider = FakeProvider("the transformer model")
    repo = Repository(Database(":memory:"))
    domain_id = import_package(repo, SEED_PATH)
    session_id = repo.start_session("teste")

    detections = _service(
        provider, repo=repo, domain_id=domain_id, session_id=session_id
    ).process(_speech())

    assert detections[0].detection_id is not None
    stored = repo.list_detections(session_id)
    assert len(stored) == 1
    assert stored[0].term_id is not None
    assert stored[0].sense_id is not None
    assert stored[0].method == "matcher"


def test_context_snippet_respects_privacy_flag():
    provider = FakeProvider("the transformer model")
    repo = Repository(Database(":memory:"))
    domain_id = import_package(repo, SEED_PATH)

    priv_session = repo.start_session("priv")
    _service(
        provider,
        repo=repo,
        domain_id=domain_id,
        session_id=priv_session,
        save_context=False,
    ).process(_speech())
    assert repo.list_detections(priv_session)[0].context_snippet is None

    save_session = repo.start_session("save")
    _service(
        FakeProvider("the transformer model"),
        repo=repo,
        domain_id=domain_id,
        session_id=save_session,
        save_context=True,
    ).process(_speech())
    assert "transformer" in repo.list_detections(save_session)[0].context_snippet


def test_no_repo_means_no_persistence_id():
    provider = FakeProvider("the transformer model")

    detections = _service(provider).process(_speech())

    assert detections[0].detection_id is None


def test_process_pcm_segments_and_detects():
    provider = FakeProvider("the transformer model")

    detections = _service(provider).process_pcm(_tone_pcm(600))

    assert [d.term for d in detections] == ["transformer"]
