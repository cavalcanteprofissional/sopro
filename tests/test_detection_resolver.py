"""Integração entre o serviço de detecção e o resolvedor de acepções (Fase 3)."""

from sopro.app.detection import DetectionService
from sopro.core.glossary.package import load_package
from sopro.core.matcher import MatcherConfig
from sopro.core.rag import SenseResolver, default_embedder
from sopro.core.repo import Database, Repository, import_package
from sopro.core.stt.provider import STTProvider, Transcript
from sopro.core.vad import SpeechSegment

SEED_PATH = "data/domains/tech-en-pt"


class QueueProvider(STTProvider):
    def __init__(self, *texts: str) -> None:
        self._texts = list(texts)
        self.index = 0

    def warmup(self) -> None:
        pass

    def transcribe(self, segment) -> Transcript:
        text = self._texts[self.index]
        self.index += 1
        return Transcript(text=text, start_ms=0, end_ms=0, source=segment.source)

    def close(self) -> None:
        pass


class RecordingResolver:
    def __init__(self) -> None:
        self.contexts: list[str] = []

    def resolve(self, term, context):
        self.contexts.append(context)
        return None


def _speech(end_ms: int) -> SpeechSegment:
    return SpeechSegment(start_ms=0, end_ms=end_ms, pcm=b"\x00" * 3200)


def _service(provider, package, **kwargs) -> DetectionService:
    return DetectionService(provider, package, **kwargs)


def test_resolver_selects_tech_sense_via_domain_tag():
    package = load_package(SEED_PATH)
    resolver = SenseResolver(domain_tag=package.domain_tag, embedder=default_embedder())
    provider = QueueProvider("the transformer is used for translation")

    detections = _service(provider, package, resolver=resolver).process(_speech(1000))

    assert detections[0].term == "transformer"
    assert detections[0].resolve_method == "domain_tag"
    assert "arquitetura" in detections[0].translation


def test_resolver_method_is_persisted():
    package = load_package(SEED_PATH)
    repo = Repository(Database(":memory:"))
    domain_id = import_package(repo, SEED_PATH)
    session_id = repo.start_session("teste")
    resolver = SenseResolver(domain_tag=package.domain_tag, embedder=default_embedder())
    provider = QueueProvider("the transformer is used for translation")

    detections = _service(
        provider,
        package,
        repo=repo,
        domain_id=domain_id,
        session_id=session_id,
        resolver=resolver,
    ).process(_speech(1000))

    stored = repo.list_detections(session_id)
    assert len(stored) == 1
    assert stored[0].method == "domain_tag"
    assert detections[0].detection_id == stored[0].id


def test_without_resolver_method_stays_matcher():
    package = load_package(SEED_PATH)
    provider = QueueProvider("the transformer is used")

    detections = _service(provider, package).process(_speech(1000))

    assert detections[0].resolve_method == ""


def test_context_window_accumulates_and_prunes():
    package = load_package(SEED_PATH)
    resolver = RecordingResolver()
    provider = QueueProvider(
        "first transformer", "second transformer", "third transformer"
    )
    service = _service(
        provider,
        package,
        resolver=resolver,
        context_window_s=2.0,
        matcher_config=MatcherConfig(cooldown_s=0.0, max_popups_per_minute=100),
    )

    service.process(_speech(1000))
    service.process(_speech(2000))
    service.process(_speech(5000))

    assert resolver.contexts == [
        "first transformer",
        "first transformer second transformer",
        "third transformer",
    ]


def test_context_window_disabled_uses_current_only():
    package = load_package(SEED_PATH)
    resolver = RecordingResolver()
    provider = QueueProvider("first transformer", "second transformer")
    service = _service(
        provider,
        package,
        resolver=resolver,
        context_window_s=0.0,
        matcher_config=MatcherConfig(cooldown_s=0.0, max_popups_per_minute=100),
    )

    service.process(_speech(1000))
    service.process(_speech(2000))

    assert resolver.contexts == ["first transformer", "second transformer"]
