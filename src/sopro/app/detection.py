"""Serviço de detecção: transcreve, casa termos, persiste e enfileira pop-ups.

Liga as peças do pipeline (docs/02 §3): recebe um ``SpeechSegment`` (saída do VAD),
transcreve via ``STTProvider``, casa com o ``Matcher`` (que já aplica cooldown e
orçamento, docs/02 §4.5), grava a detecção no ``Repository`` e oferece o cartão à
``PopupQueue``. É independente de UI e de SO — os adaptadores concretos (overlay
Qt, captura de áudio) ficam em ``sopro.platform`` e são injetados pelo app.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from typing import Callable

from sopro.core.audio.contracts import SAMPLE_RATE_HZ, SOURCE_SYSTEM
from sopro.core.glossary.package import DomainPackage, Sense, Term
from sopro.core.matcher import Matcher, MatcherConfig
from sopro.core.repo import Repository
from sopro.core.stt.provider import AudioSegment, STTProvider
from sopro.core.stt.vocabulary import vocabulary_hint
from sopro.core.vad import SpeechSegment, VadConfig, segment
from sopro.platform.popup import PopupItem, PopupQueue


@dataclass(frozen=True)
class Detection:
    """Um termo detectado em um trecho, pronto para exibição e histórico."""

    term: str
    surface: str
    source: str
    start_ms: int
    end_ms: int
    ambiguous: bool
    sense_count: int
    pos: str = ""
    translation: str = ""
    definition: str = ""
    register: str | None = None
    detection_id: int | None = None


def _primary_sense(term: Term) -> Sense | None:
    """Acepção primária: menor ordinal (desambiguação contextual vem na Fase 3)."""
    if not term.senses:
        return None
    return min(term.senses, key=lambda sense: sense.ordinal)


class DetectionService:
    """Orquestra detecção de termos a partir de segmentos de fala."""

    def __init__(
        self,
        provider: STTProvider,
        package: DomainPackage,
        *,
        matcher: Matcher | None = None,
        matcher_config: MatcherConfig | None = None,
        repo: Repository | None = None,
        domain_id: int | None = None,
        session_id: int | None = None,
        popup: PopupQueue | None = None,
        save_context: bool = False,
        language: str = "en",
        vocab_limit: int | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._provider = provider
        self._package = package
        self._terms: dict[str, Term] = {t.canonical_en: t for t in package.terms}
        self._matcher = matcher or Matcher(package, matcher_config)
        self._repo = repo
        self._domain_id = domain_id
        self._session_id = session_id
        self._popup = popup
        self._save_context = save_context
        self._language = language
        self._hint = (
            vocabulary_hint(package, vocab_limit)
            if vocab_limit is not None
            else vocabulary_hint(package)
        )
        self._clock = clock or time.monotonic

    @property
    def popup(self) -> PopupQueue | None:
        return self._popup

    def process(
        self, speech: SpeechSegment, source: str = SOURCE_SYSTEM
    ) -> list[Detection]:
        """Transcreve um segmento e devolve as detecções (já persistidas/enfileiradas)."""
        transcript = self._provider.transcribe(
            AudioSegment(
                pcm=speech.pcm,
                sample_rate=SAMPLE_RATE_HZ,
                source=source,
                language=self._language,
                vocabulary_hint=self._hint,
            )
        )
        detections: list[Detection] = []
        for match in self._matcher.match(transcript.text):
            detection = self._build(match, speech, source)
            detection_id = self._persist(detection, transcript.text)
            if detection_id is not None:
                detection = replace(detection, detection_id=detection_id)
            self._enqueue(detection)
            detections.append(detection)
        return detections

    def process_pcm(
        self,
        pcm: bytes,
        source: str = SOURCE_SYSTEM,
        vad_config: VadConfig | None = None,
    ) -> list[Detection]:
        """Segmenta PCM 16-bit mono e processa cada trecho (uso offline/testes)."""
        detections: list[Detection] = []
        for speech in segment(pcm, vad_config):
            detections.extend(self.process(speech, source=source))
        return detections

    def _build(self, match, speech: SpeechSegment, source: str) -> Detection:
        term = self._terms.get(match.term)
        sense = _primary_sense(term) if term else None
        return Detection(
            term=match.term,
            surface=match.surface,
            source=source,
            start_ms=speech.start_ms,
            end_ms=speech.end_ms,
            ambiguous=match.ambiguous,
            sense_count=match.sense_count,
            pos=term.pos if term else "",
            translation=sense.translation_pt if sense else "",
            definition=sense.definition_pt if sense else "",
            register=sense.register if sense else None,
        )

    def _persist(self, detection: Detection, text: str) -> int | None:
        if self._repo is None or self._session_id is None:
            return None
        term_id = None
        sense_id = None
        if self._domain_id is not None:
            record = self._repo.get_term_by_canonical(self._domain_id, detection.term)
            if record is not None:
                term_id = record.id
                for sense in self._repo.list_senses(term_id):
                    if sense.translation_pt == detection.translation:
                        sense_id = sense.id
                        break
        return self._repo.add_detection(
            self._session_id,
            term_id=term_id,
            sense_id=sense_id,
            source=detection.source,
            method="matcher",
            context_snippet=text if self._save_context else None,
        )

    def _enqueue(self, detection: Detection) -> None:
        if self._popup is not None:
            self._popup.offer(
                PopupItem(key=detection.term, payload=detection), now=self._clock()
            )
