"""Fallback de hotword usando STT curto + VAD."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable

import numpy as np
import sounddevice as sd

from sopro.core.hotword.detector import DetCallback, HotwordDetector
from sopro.core.vad import VadConfig, segment


class SttShortHotwordDetector(HotwordDetector):
    def __init__(
        self,
        phrase: str = "sopro",
        sensitivity: float = 0.5,
        device: str | None = None,
        **kwargs,
    ):
        self._phrase = (phrase or "sopro").lower().strip()
        self._sensitivity = sensitivity
        self._device = device
        self._callbacks: list[DetCallback] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._enabled = True

    def register_callback(self, callback: DetCallback) -> None:
        self._callbacks.append(callback)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._stop.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._running:
            return
        self._stop.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _trigger(self) -> None:
        for cb in list(self._callbacks):
            try:
                cb()
            except Exception:
                pass

    def _run(self) -> None:
        try:
            # capture 16kHz mono short chunks
            rate = 16000
            chunk = 1024
            with sd.InputStream(
                device=self._device,
                channels=1,
                samplerate=rate,
                blocksize=chunk,
                dtype="int16",
            ) as stream:
                buf = []
                last = time.time()
                while not self._stop.is_set():
                    if not self._enabled:
                        time.sleep(0.01)
                        continue
                    data, _ = stream.read(chunk)
                    buf.append(data)
                    now = time.time()
                    if now - last > 0.8:  # check every 0.8s
                        last = now
                        pcm = np.concatenate(buf, axis=0).flatten()
                        buf.clear()
                        # quick VAD segments
                        vad_cfg = VadConfig()
                        segments = list(segment(pcm, vad_cfg))
                        if segments:
                            # concat speech
                            audio = np.concatenate([s.pcm for s in segments]).astype(np.float32)
                            audio /= 32768.0
                            # try tiny quick check via faster-whisper if installed
                            try:
                                from faster_whisper import WhisperModel

                                model = WhisperModel(
                                    "tiny.en",
                                    device="cpu",
                                    compute_type="int8",
                                    download_root=None,
                                    local_files_only=False,
                                )
                                segments_res, _ = model.transcribe(
                                    audio,
                                    language="en",
                                    beam_size=1,
                                    vad_filter=False,
                                    initial_prompt=None,
                                    word_timestamps=False,
                                )
                                text = " ".join([s.text for s in segments_res]).lower()
                                if self._phrase in text:
                                    self._trigger()
                                    time.sleep(0.8)
                                    model = None
                            except Exception:
                                pass
                    time.sleep(0.001)
        except Exception:
            self._running = False
        finally:
            self._running = False
