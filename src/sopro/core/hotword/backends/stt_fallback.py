"""Fallback de hotword usando STT curto + VAD, alimentado pelo pipeline.

Não abre dispositivo de áudio: recebe os mesmos quadros PCM da captura principal
via ``feed()``. O modelo é carregado uma única vez dentro de uma thread de trabalho,
e o callback é disparado com debounce. Nenhum conteúdo de fala é logado.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

from sopro.core.audio import SAMPLE_RATE_HZ
from sopro.core.hotword.detector import DetCallback, HotwordDetector
from sopro.core.stt import AudioSegment, STTProvider
from sopro.core.text.normalize import normalize
from sopro.core.vad import SpeechSegment, VadConfig
from sopro.core.vad.streaming import StreamingSegmenter

log = logging.getLogger("sopro")

_MAX_QUEUED_FRAMES = 128
_DEBOUNCE_S = 1.5
_SILENCE_PAD = b"\x00\x00" * (SAMPLE_RATE_HZ // 10)


class SttShortHotwordDetector(HotwordDetector):
    """Detecta a frase por transcrição curta, sem captura própria."""

    def __init__(
        self,
        phrase: str = "sopro",
        sensitivity: float = 0.5,
        device: str | None = None,
        provider_factory: Callable[[], STTProvider] | None = None,
        **kwargs,
    ):
        self._phrase = normalize(phrase or "sopro")
        self._sensitivity = float(max(0.0, min(1.0, sensitivity)))
        self._device = device
        self._provider_factory = provider_factory
        self._provider: STTProvider | None = None
        self._callbacks: list[DetCallback] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._enabled = True
        self._queue: queue.Queue[tuple[str, bytes] | None] = queue.Queue(
            maxsize=_MAX_QUEUED_FRAMES
        )
        self._last_trigger = 0.0
        self._mute_until = 0.0
        self._reset = threading.Event()

    def register_callback(self, callback: DetCallback) -> None:
        self._callbacks.append(callback)

    def mute(self, seconds: float = 2.0) -> None:
        """Descarta áudio por alguns segundos (evita ouvir os próprios sons)."""
        self._mute_until = time.monotonic() + max(0.0, seconds)
        self._reset.set()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    @property
    def running(self) -> bool:
        return self._running

    def feed(self, pcm: bytes, source: str = "system") -> None:
        if (
            not self._running
            or not self._enabled
            or not pcm
            or time.monotonic() < self._mute_until
        ):
            return
        try:
            self._queue.put_nowait((source, bytes(pcm)))
        except queue.Full:
            # Áudio é descartável: perder um quadro é melhor que bloquear a captura.
            return

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="sopro-hotword", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        provider = self._provider
        self._provider = None
        if provider is not None:
            try:
                provider.close()
            except Exception:
                log.debug("falha ao fechar provider do hotword", exc_info=True)

    def _trigger(self) -> None:
        for callback in list(self._callbacks):
            try:
                callback()
            except Exception:
                log.debug("callback de hotword falhou", exc_info=True)

    def _matches(self, text: str) -> bool:
        normalized = normalize(text)
        if not self._phrase:
            return False
        if self._phrase in normalized:
            return True
        compact = normalized.replace(" ", "")
        phrase = self._phrase.replace(" ", "")
        return bool(phrase) and phrase in compact

    def _audio(self, speech: SpeechSegment) -> AudioSegment:
        return AudioSegment(
            pcm=_SILENCE_PAD + speech.pcm + _SILENCE_PAD,
            source="system",
            vocabulary_hint=(self._phrase,),
        )

    def _get_provider(self) -> STTProvider | None:
        if self._provider is None and self._provider_factory is not None:
            try:
                self._provider = self._provider_factory()
                self._provider.warmup()
            except Exception as exc:  # noqa: BLE001 - recurso opcional
                log.warning("hotword indisponível: %s", exc)
                self._provider = None
                self._enabled = False
        return self._provider

    def _heard(self, speech: SpeechSegment) -> bool:
        provider = self._get_provider()
        if provider is None:
            return False
        try:
            transcript = provider.transcribe(self._audio(speech))
        except Exception:
            log.debug("transcrição do hotword falhou", exc_info=True)
            return False
        return self._matches(transcript.text)

    def _run(self) -> None:
        energy = 0.02 - 0.015 * self._sensitivity
        config = VadConfig(
            energy_threshold=max(0.002, energy),
            min_speech_ms=250,
            min_silence_ms=350,
            max_segment_ms=3_500,
            overlap_ms=0,
        )
        segmenters: dict[str, StreamingSegmenter] = {}
        try:
            while not self._stop.is_set():
                if self._reset.is_set():
                    self._reset.clear()
                    segmenters.clear()
                try:
                    item = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                if item is None:
                    break
                if time.monotonic() < self._mute_until:
                    continue
                if not self._enabled:
                    continue
                source, pcm = item
                segmenter = segmenters.get(source)
                if segmenter is None:
                    segmenter = StreamingSegmenter(config)
                    segmenters[source] = segmenter
                for speech in segmenter.feed(pcm):
                    if self._stop.is_set() or not self._enabled:
                        break
                    if not self._heard(speech):
                        continue
                    now = time.monotonic()
                    if now - self._last_trigger < _DEBOUNCE_S:
                        continue
                    self._last_trigger = now
                    self._trigger()
            for segmenter in segmenters.values():
                for speech in segmenter.flush():
                    if self._heard(speech):
                        self._trigger()
                        return
        finally:
            self._running = False
