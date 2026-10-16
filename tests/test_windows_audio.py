"""Testes da captura no Windows (PyAudioWPatch simulado, sem hardware)."""

import array

import pytest

from sopro.core.audio import (
    SOURCE_MIC,
    SOURCE_SYSTEM,
    AudioSource,
    AudioUnavailable,
    CaptureConfig,
    DeviceKind,
    DeviceNotFound,
)
from sopro.platform.audio import windows
from sopro.platform.audio.windows import WindowsAudioSource

_MIC = {
    "name": "Microphone (Realtek)",
    "maxInputChannels": 1,
    "maxOutputChannels": 0,
    "defaultSampleRate": 48_000.0,
}
_LOOPBACK = {
    "name": "Speakers (loopback)",
    "maxInputChannels": 2,
    "maxOutputChannels": 0,
    "defaultSampleRate": 48_000.0,
    "isLoopbackDevice": True,
}
_OUTPUT = {
    "name": "Speakers",
    "maxInputChannels": 0,
    "maxOutputChannels": 2,
    "defaultSampleRate": 48_000.0,
}
_DEVICES = [_MIC, _LOOPBACK, _OUTPUT]


class FakeStream:
    def __init__(self):
        self.stopped = False
        self.closed = False

    def stop_stream(self):
        self.stopped = True

    def close(self):
        self.closed = True


class FakePyAudio:
    paInt16 = 8
    paContinue = 0
    paComplete = 1

    def __init__(self, devices=_DEVICES, default_input=0, default_loopback=1):
        self._devices = devices
        self._default_input = default_input
        self._default_loopback = default_loopback
        self.opened = []
        self.terminated = False

    def get_device_count(self):
        return len(self._devices)

    def get_device_info_by_index(self, index):
        return self._devices[index]

    def get_default_input_device_info(self):
        return {"index": self._default_input}

    def get_default_wasapi_loopback(self):
        return {"index": self._default_loopback}

    def open(self, **kwargs):
        stream = FakeStream()
        self.opened.append((kwargs, stream))
        return stream

    def terminate(self):
        self.terminated = True


class FakeModule:
    paInt16 = 8
    paContinue = 0
    paComplete = 1

    def __init__(self, backend):
        self._backend = backend

    def PyAudio(self):  # noqa: N802 - paridade com a API do PyAudio
        return self._backend


def _source(backend):
    return WindowsAudioSource(pyaudio_module=FakeModule(backend))


def test_list_devices_maps_kinds_and_sources():
    source = _source(FakePyAudio())

    devices = source.list_devices()

    assert [device.id for device in devices] == ["0", "1", "2"]
    mic, loop, out = devices
    assert mic.kind is DeviceKind.INPUT and mic.source == SOURCE_MIC and mic.is_default
    assert loop.kind is DeviceKind.LOOPBACK and loop.source == SOURCE_SYSTEM
    assert out.kind is DeviceKind.OUTPUT and out.source is None


def test_resolve_default_loopback_device():
    backend = FakePyAudio()
    source = _source(backend)

    with source:
        source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))

    opened_index = backend.opened[0][0]["input_device_index"]
    assert opened_index == 1


def test_resolve_default_mic_device():
    backend = FakePyAudio()
    source = _source(backend)

    with source:
        source.start(CaptureConfig(sources=(SOURCE_MIC,)))

    assert backend.opened[0][0]["input_device_index"] == 0


def test_start_missing_device_raises():
    backend = FakePyAudio(devices=[_MIC], default_input=0, default_loopback=None)
    source = _source(backend)

    with pytest.raises(DeviceNotFound):
        source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))


def test_opens_stream_in_callback_mode():
    backend = FakePyAudio()
    source = _source(backend)

    with source:
        source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))

    kwargs = backend.opened[0][0]
    assert callable(kwargs["stream_callback"])
    assert kwargs["input"] is True


def test_callback_converts_frame_to_16k_mono():
    stereo_48k = array.array("h", [1000, 1000] * 480).tobytes()  # 10 ms estéreo 48k
    backend = FakePyAudio()
    source = _source(backend)
    source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))
    callback = backend.opened[0][0]["stream_callback"]

    callback(stereo_48k, 480, None, 0)
    frame = source.read(timeout=0)

    assert frame is not None
    assert frame.source == SOURCE_SYSTEM
    assert frame.sample_rate == 16_000
    assert len(frame.pcm) == 2 * 160
    source.close()


def test_callback_stops_after_close():
    backend = FakePyAudio()
    source = _source(backend)
    source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))
    callback = backend.opened[0][0]["stream_callback"]

    source.close()
    _data, flag = callback(b"\x00\x00" * 480, 480, None, 0)

    assert flag == FakeModule.paComplete


def test_close_stops_streams_and_terminates():
    backend = FakePyAudio()
    source = _source(backend)
    source.start(CaptureConfig(sources=(SOURCE_SYSTEM,)))
    stream = backend.opened[0][1]

    source.close()

    assert stream.stopped and stream.closed
    assert backend.terminated


def test_missing_dependency_raises_audio_unavailable(monkeypatch):
    def boom():
        raise AudioUnavailable("PyAudioWPatch não está instalado")

    monkeypatch.setattr(windows, "_import_pyaudio", boom)
    source = WindowsAudioSource()

    with pytest.raises(AudioUnavailable):
        source.list_devices()


def test_is_audio_source():
    assert issubclass(WindowsAudioSource, AudioSource)
