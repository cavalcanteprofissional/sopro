"""Segmentação de fala incremental para áudio em fluxo (docs/02 §5).

Enquanto ``core.vad.energy.segment`` processa um buffer PCM completo, esta classe
consome quadros conforme chegam (captura em tempo real) e emite ``SpeechSegment``
assim que um trecho de fala termina. Reaproveita os mesmos parâmetros do
``VadConfig`` e usa o RMS de ``core.audio.pcm``.

Comportamento:
- inicia a coleta no primeiro quadro acima do limiar de energia;
- finaliza o trecho após ``min_silence_ms`` de silêncio (descarta se a fala for
  menor que ``min_speech_ms``);
- divide trechos longos em blocos de ``max_segment_ms`` com ``overlap_ms``.

Diferença para o modo offline: não há preenchimento (*pad*) no início do trecho,
pois o áudio anterior já foi descartado do fluxo.
"""

from __future__ import annotations

from sopro.core.audio.pcm import rms
from sopro.core.vad.segmenter import SpeechSegment, VadConfig


class StreamingSegmenter:
    """Converte um fluxo de PCM 16-bit mono em trechos de fala."""

    def __init__(self, config: VadConfig | None = None) -> None:
        self._config = config or VadConfig()
        self._frame_bytes = max(
            2, self._config.sample_rate * self._config.frame_ms // 1000 * 2
        )
        self.reset()

    @property
    def config(self) -> VadConfig:
        return self._config

    def reset(self) -> None:
        self._residual = bytearray()
        self._frame_index = 0
        self._collecting = False
        self._pending = bytearray()
        self._pending_start_ms = 0
        self._speech_frames = 0
        self._silence_frames = 0

    def feed(self, pcm: bytes) -> list[SpeechSegment]:
        """Consome bytes de PCM e devolve os trechos de fala concluídos."""
        self._residual += pcm
        segments: list[SpeechSegment] = []
        while len(self._residual) >= self._frame_bytes:
            frame = bytes(self._residual[: self._frame_bytes])
            del self._residual[: self._frame_bytes]
            segments.extend(self._consume(frame))
            self._frame_index += 1
        return segments

    def flush(self) -> list[SpeechSegment]:
        """Encerra o fluxo emitindo um trecho em andamento, se houver."""
        if not self._collecting or not self._pending:
            return []
        segment = self._finalize()
        return [segment] if segment else []

    # -- interno ------------------------------------------------------------
    def _consume(self, frame: bytes) -> list[SpeechSegment]:
        is_speech = rms(frame) >= self._config.energy_threshold
        out: list[SpeechSegment] = []

        if not self._collecting:
            if not is_speech:
                return out
            self._collecting = True
            self._pending = bytearray(frame)
            self._pending_start_ms = self._frame_index * self._config.frame_ms
            self._speech_frames = 1
            self._silence_frames = 0
        else:
            self._pending += frame
            if is_speech:
                self._speech_frames += 1
                self._silence_frames = 0
            else:
                self._silence_frames += 1

        if self._duration_ms() >= self._config.max_segment_ms:
            out.append(self._split())
        elif self._silence_frames * self._config.frame_ms >= self._config.min_silence_ms:
            segment = self._finalize()
            if segment is not None:
                out.append(segment)
        return out

    def _duration_ms(self) -> int:
        return (len(self._pending) // 2) * 1000 // self._config.sample_rate

    def _finalize(self) -> SpeechSegment | None:
        pcm = bytes(self._pending)
        start = self._pending_start_ms
        speech_frames = self._speech_frames
        self._collecting = False
        self._pending = bytearray()
        self._speech_frames = 0
        self._silence_frames = 0
        if speech_frames * self._config.frame_ms < self._config.min_speech_ms:
            return None
        end = start + (len(pcm) // 2) * 1000 // self._config.sample_rate
        return SpeechSegment(start_ms=start, end_ms=end, pcm=pcm)

    def _split(self) -> SpeechSegment:
        pcm = bytes(self._pending)
        start = self._pending_start_ms
        end = start + (len(pcm) // 2) * 1000 // self._config.sample_rate

        overlap_bytes = int(self._config.sample_rate * self._config.overlap_ms / 1000) * 2
        if overlap_bytes and len(pcm) > overlap_bytes:
            self._pending = bytearray(pcm[-overlap_bytes:])
            self._pending_start_ms = end - self._config.overlap_ms
            self._speech_frames = max(
                1, round(self._config.overlap_ms / self._config.frame_ms)
            )
        else:
            self._pending = bytearray()
            self._pending_start_ms = end
            self._speech_frames = 0
        self._silence_frames = 0
        self._collecting = True
        return SpeechSegment(start_ms=start, end_ms=end, pcm=pcm)
