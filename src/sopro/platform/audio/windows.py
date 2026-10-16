"""Captura de áudio no Windows via WASAPI (loopback do sistema + microfone).

Usa **PyAudioWPatch** (fork do PyAudio com suporte a loopback WASAPI; licença MIT).
O módulo é importado sob demanda: o núcleo não depende dele. Cada stream entrega
buffers por *callback* do PortAudio, convertidos para PCM 16-bit mono 16 kHz e
enfileirados como :class:`AudioFrame`.

Por que *callback* e não ``read`` bloqueante: em loopback, quando nada está tocando
o ``read`` pode bloquear indefinidamente e travar o ``close``. No modo callback o
PortAudio entrega os buffers (inclusive silêncio) na sua própria thread, e o
encerramento é limpo.

Armadilhas conhecidas de loopback no Windows (docs/05 A2):

- O loopback só existe sobre um **dispositivo de saída**; se ele muda de padrão
  durante a captura, o stream antigo fica mudo — é preciso reabrir.
- A taxa nativa costuma ser 48 kHz (mixer do Windows); reamostramos para 16 kHz.
- Abrimos na taxa nativa reportada pelo dispositivo e convertemos depois, para
  evitar *resample* interno ou falha do WASAPI.
- Silêncio absoluto (nenhum som tocando) gera buffers de zeros, não "sem dados".
- Dispositivo desconectado levanta erro no callback; tratamos como fim do stream.

Nada é gravado em disco: o áudio vive apenas na fila em memória.
"""

from __future__ import annotations

from queue import Empty, Full, Queue
from typing import Any, Iterator

from sopro.core.audio import (
    SAMPLE_RATE_HZ,
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioFrame,
    AudioSource,
    AudioUnavailable,
    CaptureConfig,
    DeviceInfo,
    DeviceKind,
    DeviceNotFound,
    to_mono_target,
)

_DEFAULT_CHANNELS = 1
_FALLBACK_RATE = 48_000
_READ_QUEUE_MAX = 64


def _import_pyaudio():
    # PyAudioWPatch é o fork com loopback WASAPI; o módulo importa como ``pyaudiowpatch``.
    try:
        import pyaudiowpatch as pyaudio  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise AudioUnavailable(
            "PyAudioWPatch não está instalado; rode `pip install -e \".[audio]\"`"
        ) from exc
    return pyaudio


def _is_loopback(info: dict[str, Any]) -> bool:
    return bool(info.get("isLoopbackDevice"))


class WindowsAudioSource(AudioSource):
    """Fonte de áudio do Windows (WASAPI loopback e microfone)."""

    def __init__(self, *, pyaudio_module: Any | None = None) -> None:
        self._pyaudio_module = pyaudio_module
        self._module: Any | None = None
        self._pa: Any | None = None
        self._queue: Queue[AudioFrame] = Queue(maxsize=_READ_QUEUE_MAX)
        self._streams: list[Any] = []
        self._closed = False

    # -- ciclo de vida do backend -------------------------------------------
    def _backend(self) -> Any:
        if self._pa is None:
            self._module = self._pyaudio_module or _import_pyaudio()
            self._pa = self._module.PyAudio()
        return self._pa

    def _device_count(self) -> int:
        return int(self._backend().get_device_count())

    def _device_info(self, index: int) -> dict[str, Any]:
        return self._backend().get_device_info_by_index(index)

    # -- descoberta de dispositivos -----------------------------------------
    def list_devices(self) -> list[DeviceInfo]:
        default_input = self._default_index("get_default_input_device_info")
        default_loopback = self._default_loopback_index()
        devices: list[DeviceInfo] = []
        for index in range(self._device_count()):
            info = self._device_info(index)
            loopback = _is_loopback(info)
            inputs = int(info.get("maxInputChannels", 0))
            outputs = int(info.get("maxOutputChannels", 0))
            if loopback:
                kind = DeviceKind.LOOPBACK
            elif inputs > 0:
                kind = DeviceKind.INPUT
            elif outputs > 0:
                kind = DeviceKind.OUTPUT
            else:
                continue
            source = None
            if kind is DeviceKind.INPUT:
                source = SOURCE_MIC
            elif kind is DeviceKind.LOOPBACK:
                source = SOURCE_SYSTEM
            is_default = index in (default_input, default_loopback)
            devices.append(
                DeviceInfo(
                    id=str(index),
                    name=str(info.get("name", f"device {index}")),
                    kind=kind,
                    channels=max(1, inputs or outputs or 1),
                    default_sample_rate=int(
                        info.get("defaultSampleRate", _FALLBACK_RATE)
                    ),
                    is_default=is_default,
                    source=source,
                )
            )
        return devices

    @staticmethod
    def _index_of(info: Any) -> int | None:
        if not isinstance(info, dict):
            return None
        index = info.get("index")
        return int(index) if index is not None else None

    def _default_index(self, method: str) -> int | None:
        backend = self._backend()
        getter = getattr(backend, method, None)
        if getter is None:
            return None
        try:
            info = getter()
        except Exception:  # noqa: BLE001 - ausência de dispositivo padrão
            return None
        return self._index_of(info)

    def _default_loopback_index(self) -> int | None:
        backend = self._backend()
        getter = getattr(backend, "get_default_wasapi_loopback", None)
        if getter is not None:
            try:
                info = getter()
            except Exception:  # noqa: BLE001
                info = None
            index = self._index_of(info)
            if index is not None:
                return index
        for index in range(self._device_count()):
            if _is_loopback(self._device_info(index)):
                return index
        return None

    def _resolve_device(self, source: str, config: CaptureConfig) -> DeviceInfo:
        explicit = (
            config.system_device_id if source == SOURCE_SYSTEM else config.mic_device_id
        )
        devices = self.list_devices()
        if explicit is not None:
            for device in devices:
                if device.id == explicit:
                    return device
            raise DeviceNotFound(f"dispositivo {explicit!r} não encontrado")
        wanted = DeviceKind.LOOPBACK if source == SOURCE_SYSTEM else DeviceKind.INPUT
        candidates = [device for device in devices if device.kind is wanted]
        if not candidates:
            raise DeviceNotFound(f"nenhum dispositivo para a fonte {source!r}")
        for device in candidates:
            if device.is_default:
                return device
        return candidates[0]

    # -- captura -------------------------------------------------------------
    def start(self, config: CaptureConfig) -> None:
        if self._streams:
            raise AudioUnavailable("captura já iniciada")
        self._closed = False
        for source in config.sources:
            device = self._resolve_device(source, config)
            device_rate = device.default_sample_rate or _FALLBACK_RATE
            channels = device.channels or _DEFAULT_CHANNELS
            frames = max(1, device_rate * config.frame_ms // 1000)
            self._streams.append(
                self._open_stream(
                    device, device_rate, channels, frames, source, config.target_sample_rate
                )
            )

    def _open_stream(
        self,
        device: DeviceInfo,
        rate: int,
        channels: int,
        frames: int,
        source: str,
        target_rate: int,
    ) -> Any:
        backend = self._backend()
        module = self._module

        def callback(in_data, _frame_count, _time_info, _status):
            if self._closed:
                return (None, module.paComplete)
            self._put(self._make_frame(in_data, source, channels, rate, target_rate))
            return (None, module.paContinue)

        try:
            return backend.open(
                format=module.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=int(device.id),
                frames_per_buffer=frames,
                stream_callback=callback,
            )
        except Exception as exc:  # noqa: BLE001 - erros variam por driver
            raise AudioUnavailable(
                f"não foi possível abrir {device.name!r}: {exc}"
            ) from exc

    def _make_frame(
        self,
        raw: bytes,
        source: str,
        channels: int,
        device_rate: int,
        target_rate: int,
    ) -> AudioFrame:
        pcm = to_mono_target(raw, channels, device_rate, target_rate)
        return AudioFrame(pcm=pcm, source=source, sample_rate=target_rate)

    def _put(self, frame: AudioFrame) -> None:
        try:
            self._queue.put_nowait(frame)
        except Full:  # pragma: no cover - fila cheia: descarta para não travar
            pass

    def read(self, timeout: float | None = None) -> AudioFrame | None:
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def close(self) -> None:
        self._closed = True
        for stream in self._streams:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:  # noqa: BLE001
                pass
        self._streams.clear()
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:  # noqa: BLE001
                pass
            self._pa = None

    def drain(self) -> Iterator[AudioFrame]:
        """Consome os quadros disponíveis sem bloquear (útil em testes/sondas)."""
        while True:
            frame = self.read(timeout=0)
            if frame is None:
                return
            yield frame
