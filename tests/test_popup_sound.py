"""Testes do efeito sonoro dos pop-ups (WAV sintetizado em memória)."""

import io
import sys
import threading
import wave

from sopro.core.audio.chime import (
    DURATION_MS,
    SAMPLE_RATE_HZ,
    chime_wav,
    hotword_off_wav,
    hotword_on_wav,
)


def test_chime_is_a_valid_mono_wav():
    data = chime_wav()

    assert data.startswith(b"RIFF")
    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == SAMPLE_RATE_HZ
        expected = int(SAMPLE_RATE_HZ * DURATION_MS / 1000)
        assert abs(wav.getnframes() - expected) <= 1


def test_chime_has_audio_content():
    frames = chime_wav()[44:]
    assert len(frames) > 0
    assert any(byte not in (0, 0x80) for byte in frames[:2000])


def test_default_player_uses_memory_without_async(monkeypatch):
    from sopro.platform.popup import sound

    calls = []

    class FakeWinsound:
        SND_MEMORY = 0x0004
        SND_NODEFAULT = 0x0002
        SND_ASYNC = 0x0001

        @staticmethod
        def PlaySound(data, flags):
            calls.append((data, flags))

    monkeypatch.setitem(sys.modules, "winsound", FakeWinsound)

    assert sound._default_player(b"RIFF") is True
    assert calls == [(b"RIFF", FakeWinsound.SND_MEMORY | FakeWinsound.SND_NODEFAULT)]
    assert not (calls[0][1] & FakeWinsound.SND_ASYNC)


def test_public_sound_plays_on_worker_thread():
    from sopro.platform.popup import sound

    played = []
    done = threading.Event()

    def player(wav):
        played.append((wav, threading.current_thread().name))
        done.set()
        return True

    sound.set_player(player)
    try:
        sound.play_popup_sound(0.2)
        assert done.wait(2.0)
    finally:
        sound.set_player(None)

    assert played
    assert played[0][0].startswith(b"RIFF")
    assert played[0][1] == "sopro-sound"


def _samples(data: bytes):
    import array

    frames = data[44:]
    values = array.array("h")
    values.frombytes(frames)
    return values


def test_chime_has_no_clicks_and_no_wrap():
    for volume in (0.0, 0.5, 1.0):
        values = _samples(chime_wav(volume=volume))
        assert values[0] == 0
        assert values[-1] == 0
        assert max(abs(value) for value in values) <= 32767
    assert all(value == 0 for value in _samples(chime_wav(volume=0.0)))


def test_hotword_sounds_are_distinct_from_popup():
    popup = chime_wav()
    on = hotword_on_wav()
    off = hotword_off_wav()
    assert popup != on
    assert on != off


def test_before_play_hook_runs(monkeypatch):
    from sopro.platform.popup import sound

    calls = []

    class BrokenWinsound:
        @staticmethod
        def PlaySound(*_args):
            raise RuntimeError("sem áudio")

    monkeypatch.setitem(sys.modules, "winsound", BrokenWinsound)
    sound.set_before_play(lambda: calls.append(True))
    try:
        assert sound._play(b"x") is False
    finally:
        sound.set_before_play(None)
    assert calls == [True]
