"""Serviço de detecção: transcreve, casa termos, persiste e enfileira pop-ups.

Liga as peças do pipeline (docs/02 §3): recebe um ``SpeechSegment`` (saída do VAD),
transcreve via ``STTProvider``, casa com o ``Matcher`` (que já aplica cooldown e
orçamento, docs/02 §4.5), grava a detecção no ``Repository`` e oferece o cartão à
``PopupQueue``. É independente de UI e de SO — os adaptadores concretos (overlay
Qt, captura de áudio) ficam em ``sopro.platform`` e são injetados pelo app.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Callable

from sopro.core.audio.contracts import SAMPLE_RATE_HZ, SOURCE_SYSTEM
from sopro.core.glossary.package import DomainPackage, Sense, Term
from sopro.core.llm import GeneratedEntryService, RateLimiter, extract_candidates
from sopro.core.matcher import Matcher, MatcherConfig
from sopro.core.rag import Resolution, SenseResolver
from sopro.core.repo import Repository
from sopro.core.stt.provider import AudioSegment, STTProvider
from sopro.core.stt.vocabulary import vocabulary_hint
from sopro.core.vad import SpeechSegment, VadConfig, segment
from sopro.platform.popup import PopupItem, PopupQueue

log = logging.getLogger("sopro")

DEFAULT_MIN_CONFIDENCE = 0.25


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
    resolve_method: str = ""
    detection_id: int | None = None
    track: str | None = None


def _primary_sense(term: Term) -> Sense | None:
    """Acepção primária: menor ordinal, usada quando não há resolvedor."""
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
        domain_ids: Sequence[int] = (),
        active_tracks: tuple[str, ...] = (),
        session_id: int | None = None,
        popup: PopupQueue | None = None,
        resolver: SenseResolver | None = None,
        generated: GeneratedEntryService | None = None,
        candidate_limiter: RateLimiter | None = None,
        candidate_limit: int = 3,
        context_window_s: float = 0.0,
        save_context: bool = False,
        language: str = "en",
        vocab_limit: int | None = None,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._provider = provider
        self._package = package
        self._terms: dict[str, Term] = {t.canonical_en: t for t in package.terms}
        self._matcher = matcher or Matcher(package, matcher_config)
        self._repo = repo
        self._domain_id = domain_id
        self._domain_ids = tuple(domain_ids) or (
            (domain_id,) if domain_id is not None else ()
        )
        self._session_id = session_id
        self._popup = popup
        self._resolver = resolver
        self._generated = generated
        self._candidate_limiter = candidate_limiter
        self._candidate_limit = candidate_limit
        self._known = frozenset(
            [t.canonical_en.lower() for t in package.terms]
            + [alias.lower() for t in package.terms for alias in t.aliases]
        )
        self._context_window_s = context_window_s
        self._context: list[tuple[int, str]] = []
        self._save_context = save_context
        self._language = language
        self._min_confidence = max(0.0, min(1.0, min_confidence))
        self._hint = (
            vocabulary_hint(package, vocab_limit, active_tracks)
            if vocab_limit is not None
            else vocabulary_hint(package, active_tracks=active_tracks)
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
        if (
            transcript.confidence is not None
            and transcript.confidence < self._min_confidence
        ):
            log.info(
                "transcrição descartada por baixa confiança (%.3f)",
                transcript.confidence,
            )
            return []
        detections: list[Detection] = []
        context = self._context_text(speech.end_ms, transcript.text)
        for match in self._matcher.match(transcript.text):
            detection = self._build(match, speech, source, context)
            detection_id = self._persist(detection, transcript.text)
            if detection_id is not None:
                detection = replace(detection, detection_id=detection_id)
            self._enqueue(detection)
            detections.append(detection)
        detections.extend(self._generated_detections(transcript.text, speech, source))
        return detections

    def _generated_detections(
        self, text: str, speech: SpeechSegment, source: str
    ) -> list[Detection]:
        """Termos fora do glossário via LLM, com limite de taxa próprio (docs/02 §4.6)."""
        if self._generated is None or self._candidate_limiter is None or not text:
            return []
        candidates = extract_candidates(
            text,
            self._known,
            stoplist=self._package.stoplist,
            limit=self._candidate_limit,
        )
        detections: list[Detection] = []
        for candidate in candidates:
            if not self._candidate_limiter.allow():
                break
            result = self._generated.explain(candidate.surface, context=text)
            if result is None:
                continue
            detection = Detection(
                term=candidate.surface,
                surface=candidate.surface,
                source=source,
                start_ms=speech.start_ms,
                end_ms=speech.end_ms,
                ambiguous=False,
                sense_count=0,
                translation=result.translation,
                definition=result.definition,
                resolve_method="llm",
            )
            detection_id = self._persist(detection, text)
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

    def _context_text(self, end_ms: int, current: str) -> str:
        """Janela deslizante: últimos N segundos de texto transcrito (docs/05 A7)."""
        if self._context_window_s <= 0:
            return current
        self._context.append((end_ms, current))
        cutoff = end_ms - int(self._context_window_s * 1000)
        self._context = [
            (seen_ms, text) for seen_ms, text in self._context if seen_ms >= cutoff
        ]
        return " ".join(text for _seen_ms, text in self._context)

    def _sense_for(self, term: Term, text: str) -> tuple[Sense | None, str]:
        """Escolhe a acepção: resolvedor contextual (Fase 3) ou primária."""
        if self._resolver is not None:
            resolution: Resolution | None = self._resolver.resolve(term, text)
            if resolution is not None:
                return resolution.sense, resolution.method
        return _primary_sense(term), ""

    def _build(
        self, match, speech: SpeechSegment, source: str, text: str
    ) -> Detection:
        term = self._terms.get(match.term)
        sense, method = self._sense_for(term, text) if term else (None, "")
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
            resolve_method=method,
            track=sense.track if sense else None,
        )

    def _persist(self, detection: Detection, text: str) -> int | None:
        if self._repo is None or self._session_id is None:
            return None
        term_id = None
        sense_id = None
        for domain_id in self._domain_ids:
            record = self._repo.get_term_by_canonical(domain_id, detection.term)
            if record is None:
                continue
            term_id = record.id
            for sense in self._repo.list_senses(term_id):
                same_translation = sense.translation_pt == detection.translation
                same_track = not detection.track or sense.track == detection.track
                if same_translation and same_track:
                    sense_id = sense.id
                    break
            if sense_id is not None:
                break
        return self._repo.add_detection(
            self._session_id,
            term_id=term_id,
            sense_id=sense_id,
            source=detection.source,
            method=detection.resolve_method or "matcher",
            context_snippet=text if self._save_context else None,
        )

    def _enqueue(self, detection: Detection) -> None:
        if self._popup is not None:
            self._popup.offer(
                PopupItem(key=detection.term, payload=detection), now=self._clock()
            )
