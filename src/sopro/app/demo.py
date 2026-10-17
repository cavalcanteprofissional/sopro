"""Modo demonstração: áudio e transcrições falsas (plano de DX, docs/05 A3).

Permite exercitar o pipeline completo (captura → VAD → STT → matcher → pop-up) sem
microfone, sem modelos e sem rede. A fonte gera fala sintética (tom + silêncio) que
aciona o VAD, e o provedor devolve transcrições que casam com o glossário.
"""

from __future__ import annotations

import array
import time

from sopro.core.audio.contracts import SOURCE_SYSTEM, AudioSource
from sopro.core.stt.provider import STTProvider, Transcript

DEMO_TRANSCRIPTS = (
    "the transformer model relies on self attention",
    "a token is a basic unit of text",
    "gradient descent minimizes the loss",
    "the embedding layer encodes the input",
)


class DemoProvider(STTProvider):
    """Provedor STT falso que cicla por transcrições pré-definidas."""

    def __init__(self, transcripts: tuple[str, ...] = DEMO_TRANSCRIPTS) -> None:
        self._transcripts = transcripts
        self._index = 0
        self.calls = 0

    def warmup(self) -> None:
        pass

    def transcribe(self, segment) -> Transcript:
        text = self._transcripts[self._index % len(self._transcripts)]
        self._index += 1
        self.calls += 1
        return Transcript(text=text, start_ms=0, end_ms=1000, source=segment.source)

    def close(self) -> None:
        pass


def _tone_samples(duration_ms: int, rate: int, freq: int, amp: int) -> array.array:
    total = rate * duration_ms // 1000
    period = max(2, rate // freq)
    samples = array.array("h")
    for i in range(total):
        samples.append(amp if (i % period) < (period // 2) else -amp)
    return samples


def build_demo_pcm(
    rate: int = 16000, speech_ms: int = 700, silence_ms: int = 400
) -> bytes:
    """PCM 16-bit mono com um trecho de fala seguido de silêncio (aciona o VAD)."""
    speech = _tone_samples(speech_ms, rate, freq=440, amp=8000)
    silence = array.array("h", bytes(rate * silence_ms // 1000 * 2))
    return (speech + silence).tobytes()


class DemoAudioSource(AudioSource):
    """Fonte de áudio falsa que repete um padrão de fala/silêncio continuamente."""

    def __init__(self, rate: int = 16000, frame_ms: int = 30, delay: float = 0.0) -> None:
        self._rate = rate
        self._frame_bytes = max(2, rate * frame_ms // 1000 * 2)
        self._delay = delay
        pcm = build_demo_pcm(rate)
        self._frames = [
            pcm[i : i + self._frame_bytes]
            for i in range(0, len(pcm), self._frame_bytes)
        ]
        self._index = 0

    def list_devices(self):
        return []

    def start(self, config) -> None:
        self._index = 0

    def read(self, timeout: float | None = None):
        from sopro.core.audio.contracts import AudioFrame

        if self._delay:
            time.sleep(self._delay)
        if not self._frames:
            return None
        pcm = self._frames[self._index % len(self._frames)]
        self._index += 1
        if len(pcm) % 2 != 0:
            pcm = pcm[:-1]
        return AudioFrame(pcm=pcm, source=SOURCE_SYSTEM, sample_rate=self._rate)

    def close(self) -> None:
        pass
