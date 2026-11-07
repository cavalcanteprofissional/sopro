"""Loop em tempo real: captura → VAD incremental → detecção (docs/02 §5).

Consome quadros de uma ``AudioSource``, mantém um ``StreamingSegmenter`` por fonte
(sistema/microfone), e entrega cada trecho de fala ao ``DetectionService``. É
independente de UI; o app injeta a fonte concreta de plataforma.

A leitura da fonte e o processamento rodam em threads separadas, com uma fila por
fonte (o microfone tem prioridade). Assim, a captura continua enchendo o buffer
enquanto o STT transcreve, sem descartar quadros.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable

from sopro.app.detection import Detection, DetectionService
from sopro.core.audio.contracts import (
    SOURCE_LABELS,
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioFrame,
    AudioSource,
)
from sopro.core.audio.pcm import rms
from sopro.core.vad import SpeechSegment, StreamingSegmenter, VadConfig

DEFAULT_ARBITRATION_MS = 500.0
DEFAULT_QUEUE_SIZE = 256


class RealtimePipeline:
    """Liga quadros de áudio ao serviço de detecção, com VAD incremental por fonte.

    Opcionalmente reporta atividade para a UI (indicador de estado): ``on_level``
    recebe ``(nível 0..1, falando?)`` por quadro e ``on_analyzing`` recebe ``True``
    enquanto um trecho está sendo transcrito/resolvido.
    """

    def __init__(
        self,
        service: DetectionService,
        *,
        vad_config: VadConfig | None = None,
        on_level: Callable[[float, bool], None] | None = None,
        on_source_level: Callable[[str, float, bool], None] | None = None,
        on_analyzing: Callable[[bool], None] | None = None,
        on_analyzing_source: Callable[[str, bool], None] | None = None,
        on_frame: Callable[[AudioFrame], None] | None = None,
        arbitration_ms: float = DEFAULT_ARBITRATION_MS,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._service = service
        self._vad_config = vad_config or VadConfig()
        self._segmenters: dict[str, StreamingSegmenter] = {}
        self._on_level = on_level
        self._on_source_level = on_source_level
        self._on_analyzing = on_analyzing
        self._on_analyzing_source = on_analyzing_source
        self._on_frame = on_frame
        self._active_sources: set[str] | None = None
        self._arbitration_s = max(0.0, float(arbitration_ms) / 1000.0)
        self._clock = clock or time.monotonic
        self._pending: list[tuple[float, str, SpeechSegment]] = []

    @property
    def service(self) -> DetectionService:
        return self._service

    def _segmenter(self, source: str) -> StreamingSegmenter:
        segmenter = self._segmenters.get(source)
        if segmenter is None:
            segmenter = StreamingSegmenter(self._vad_config)
            self._segmenters[source] = segmenter
        return segmenter

    def set_source_active(self, source: str, active: bool) -> None:
        """Liga/desliga a detecção de uma fonte sem parar a captura dela."""
        if self._active_sources is None:
            self._active_sources = set(SOURCE_LABELS)
        if active:
            self._active_sources.add(source)
        else:
            self._active_sources.discard(source)
        segmenter = self._segmenters.get(source)
        if segmenter is not None:
            segmenter.reset()

    def is_source_active(self, source: str) -> bool:
        return self._active_sources is None or source in self._active_sources

    def _report_level(self, source: str, pcm: bytes) -> None:
        value = rms(pcm)
        threshold = float(self._vad_config.energy_threshold)
        level = min(1.0, value / (threshold * 4.0)) if threshold > 0 else 0.0
        speaking = value >= threshold
        if self._on_source_level is not None:
            self._on_source_level(source, level, speaking)
        if self._on_level is not None:
            self._on_level(level, speaking)

    def _mic_arbitrates(self) -> bool:
        return (
            self._arbitration_s > 0
            and self._active_sources is not None
            and SOURCE_MIC in self._active_sources
        )

    def _process(self, speech: SpeechSegment, source: str) -> list[Detection]:
        if self._on_analyzing is not None:
            self._on_analyzing(True)
        if self._on_analyzing_source is not None:
            self._on_analyzing_source(source, True)
        try:
            return self._service.process(speech, source=source)
        finally:
            if self._on_analyzing_source is not None:
                self._on_analyzing_source(source, False)
            if self._on_analyzing is not None:
                self._on_analyzing(False)

    def flush_pending(
        self, now: float | None = None, *, force: bool = False
    ) -> list[Detection]:
        """Processa trechos do sistema cuja janela de arbitragem expirou."""
        if not self._pending:
            return []
        current = self._clock() if now is None else now
        ready: list[tuple[str, SpeechSegment]] = []
        waiting: list[tuple[float, str, SpeechSegment]] = []
        for deadline, source, speech in self._pending:
            if force or deadline <= current:
                ready.append((source, speech))
            else:
                waiting.append((deadline, source, speech))
        self._pending = waiting
        detections: list[Detection] = []
        for source, speech in ready:
            detections.extend(self._process(speech, source))
        return detections

    def handle_frame(self, frame: AudioFrame) -> list[Detection]:
        """Alimenta um quadro e devolve as detecções dos trechos concluídos."""
        if self._on_frame is not None:
            self._on_frame(frame)
        self._report_level(frame.source, frame.pcm)
        detections = self.flush_pending()
        if not self.is_source_active(frame.source):
            return detections
        for speech in self._segmenter(frame.source).feed(frame.pcm):
            if frame.source == SOURCE_SYSTEM and self._mic_arbitrates():
                self._pending.append(
                    (self._clock() + self._arbitration_s, frame.source, speech)
                )
                continue
            detections.extend(self._process(speech, frame.source))
            if frame.source == SOURCE_MIC:
                detections.extend(self.flush_pending(force=True))
        return detections

    def drain(self) -> list[Detection]:
        """Encerra a coleta emitindo os trechos em andamento de cada fonte."""
        pending: list[tuple[str, SpeechSegment]] = []
        for source, segmenter in self._segmenters.items():
            if not self.is_source_active(source):
                continue
            pending.extend((source, speech) for speech in segmenter.flush())
        detections: list[Detection] = []
        for source, speech in pending:
            if source == SOURCE_MIC:
                detections.extend(self._process(speech, source))
        detections.extend(self.flush_pending(force=True))
        for source, speech in pending:
            if source != SOURCE_MIC:
                detections.extend(self._process(speech, source))
        return detections

    def _emit(self, detections: list[Detection], callback) -> None:
        if callback is None:
            return
        for detection in detections:
            callback(detection)

    def _next_queued(self, queues: dict[str, queue.Queue]) -> AudioFrame | None:
        order = [SOURCE_MIC]
        order.extend(source for source in queues if source != SOURCE_MIC)
        for source in order:
            try:
                return queues[source].get_nowait()
            except queue.Empty:
                continue
        return None

    def _consume(
        self,
        queues: dict[str, queue.Queue],
        stop: threading.Event,
        wake: threading.Event,
        errors: list[BaseException],
        on_detection: Callable[[Detection], None] | None,
    ) -> None:
        try:
            while True:
                frame = self._next_queued(queues)
                if frame is not None:
                    self._emit(self.handle_frame(frame), on_detection)
                    continue
                self._emit(self.flush_pending(), on_detection)
                if stop.is_set() and all(q.empty() for q in queues.values()):
                    break
                wake.wait(0.02)
                wake.clear()
        except BaseException as exc:  # noqa: BLE001 - repassa ao chamador
            errors.append(exc)
            stop.set()
            wake.set()
            return
        try:
            self._emit(self.drain(), on_detection)
        except BaseException as exc:  # noqa: BLE001 - repassa ao chamador
            errors.append(exc)

    def run(
        self,
        source: AudioSource,
        *,
        poll_timeout: float = 0.1,
        should_stop: Callable[[], bool] | None = None,
        on_detection: Callable[[Detection], None] | None = None,
        queue_size: int = DEFAULT_QUEUE_SIZE,
    ) -> None:
        """Lê a fonte até ``should_stop`` devolver ``True`` (ou para sempre)."""
        queues: dict[str, queue.Queue] = {
            name: queue.Queue(maxsize=max(1, queue_size)) for name in SOURCE_LABELS
        }
        stop = threading.Event()
        wake = threading.Event()
        errors: list[BaseException] = []
        worker = threading.Thread(
            target=self._consume,
            args=(queues, stop, wake, errors, on_detection),
            name="sopro-pipeline",
            daemon=True,
        )
        worker.start()
        try:
            while not (should_stop is not None and should_stop()):
                if stop.is_set():
                    break
                frame = source.read(poll_timeout)
                if frame is None:
                    continue
                target = queues.setdefault(
                    frame.source, queue.Queue(maxsize=max(1, queue_size))
                )
                while not stop.is_set():
                    try:
                        target.put(frame, timeout=0.05)
                        wake.set()
                        break
                    except queue.Full:
                        continue
        finally:
            stop.set()
            wake.set()
            worker.join()
        if errors:
            raise errors[0]


def default_frame(pcm: bytes, source: str = SOURCE_SYSTEM) -> AudioFrame:
    """Atalho para montar um ``AudioFrame`` 16 kHz mono (útil em testes/demo)."""
    return AudioFrame(pcm=pcm, source=source)
