"""Loop em tempo real: captura → VAD incremental → detecção (docs/02 §5).

Consome quadros de uma ``AudioSource``, mantém um ``StreamingSegmenter`` por fonte
(sistema/microfone), e entrega cada trecho de fala ao ``DetectionService``. É
independente de UI; o app injeta a fonte concreta de plataforma.

As duas fontes são processadas em um único laço hoje (cooldown/orçamento já são por
termo, no ``Matcher``); concorrência dedicada por fonte pode ser adicionada depois.
"""

from __future__ import annotations

from typing import Callable

from sopro.app.detection import Detection, DetectionService
from sopro.core.audio.contracts import SOURCE_SYSTEM, AudioFrame, AudioSource
from sopro.core.vad import StreamingSegmenter, VadConfig


class RealtimePipeline:
    """Liga quadros de áudio ao serviço de detecção, com VAD incremental por fonte."""

    def __init__(
        self,
        service: DetectionService,
        *,
        vad_config: VadConfig | None = None,
    ) -> None:
        self._service = service
        self._vad_config = vad_config or VadConfig()
        self._segmenters: dict[str, StreamingSegmenter] = {}

    @property
    def service(self) -> DetectionService:
        return self._service

    def _segmenter(self, source: str) -> StreamingSegmenter:
        segmenter = self._segmenters.get(source)
        if segmenter is None:
            segmenter = StreamingSegmenter(self._vad_config)
            self._segmenters[source] = segmenter
        return segmenter

    def handle_frame(self, frame: AudioFrame) -> list[Detection]:
        """Alimenta um quadro e devolve as detecções dos trechos concluídos."""
        detections: list[Detection] = []
        for speech in self._segmenter(frame.source).feed(frame.pcm):
            detections.extend(self._service.process(speech, source=frame.source))
        return detections

    def drain(self) -> list[Detection]:
        """Encerra a coleta emitindo os trechos em andamento de cada fonte."""
        detections: list[Detection] = []
        for source, segmenter in self._segmenters.items():
            for speech in segmenter.flush():
                detections.extend(self._service.process(speech, source=source))
        return detections

    def run(
        self,
        source: AudioSource,
        *,
        poll_timeout: float = 0.1,
        should_stop: Callable[[], bool] | None = None,
        on_detection: Callable[[Detection], None] | None = None,
    ) -> None:
        """Lê a fonte até ``should_stop`` devolver ``True`` (ou para sempre)."""
        while not (should_stop is not None and should_stop()):
            frame = source.read(poll_timeout)
            if frame is None:
                continue
            for detection in self.handle_frame(frame):
                if on_detection is not None:
                    on_detection(detection)
        for detection in self.drain():
            if on_detection is not None:
                on_detection(detection)


def default_frame(pcm: bytes, source: str = SOURCE_SYSTEM) -> AudioFrame:
    """Atalho para montar um ``AudioFrame`` 16 kHz mono (útil em testes/demo)."""
    return AudioFrame(pcm=pcm, source=source)
