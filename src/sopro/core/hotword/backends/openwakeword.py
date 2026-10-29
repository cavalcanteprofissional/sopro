"""Backend openWakeWord (ONNX)."""
from __future__ import annotations

import threading
import time
from collections.abc import Callable

import numpy as np

from sopro.core.hotword.detector import DetCallback, HotwordDetector


class OpenWakeWordDetector(HotwordDetector):
    def __init__(
        self,
        phrase: str = "sopro",
        sensitivity: float = 0.5,
        device: str | None = None,
        **kwargs,
    ):
        self._phrase = (phrase or "sopro").lower().strip()
        self._sensitivity = float(max(0.0, min(1.0, sensitivity)))
        self._device = device
        self._callbacks: list[DetCallback] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._enabled = True
        self._model = None
        try:
            import openwakeword
            from openwakeword.model import Model

            # Try to load default models or custom
            self._oww = openwakeword
            try:
                self._model = Model()
            except Exception:
                self._model = None
        except Exception as e:
            raise

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
            import pyaudiowpatch as pyaudio

            pa = pyaudio.PyAudio()
            # Try to find default input
            rate = 16000
            chunk = 1280  # 80ms at 16kHz common for oww
            stream = None
            try:
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=chunk,
                )
            except Exception:
                try:
                    stream = pa.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        frames_per_buffer=512,
                    )
                    chunk = 512
                except Exception:
                    self._running = False
                    return
            try:
                while not self._stop.is_set() and self._enabled:
                    try:
                        data = stream.read(chunk, exception_on_overflow=False)
                    except Exception:
                        time.sleep(0.01)
                        continue
                    if not self._enabled:
                        continue
                    try:
                        audio = np.frombuffer(data, dtype=np.int16)
                        if self._model is not None:
                            # openWakeWord API varies; try predict
                            try:
                                pred = self._model.predict(audio)
                                # pred can be dict of model_name -> score
                                if isinstance(pred, dict):
                                    for name, score in pred.items():
                                        if score is None:
                                            continue
                                        s = float(score)
                                        if s >= self._sensitivity:
                                            # check if matches phrase
                                            if self._phrase and self._phrase in name.lower():
                                                self._trigger()
                                                time.sleep(0.8)  # debounce
                                                break
                                elif isinstance(pred, (list, tuple)) and pred:
                                    # some versions return scores
                                    try:
                                        s = float(pred[0])
                                        if s >= self._sensitivity:
                                            self._trigger()
                                            time.sleep(0.8)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
                    time.sleep(0.001)
            finally:
                try:
                    if stream:
                        stream.stop_stream()
                        stream.close()
                except Exception:
                    pass
                try:
                    pa.terminate()
                except Exception:
                    pass
        except Exception:
            self._running = False
        finally:
            self._running = False
