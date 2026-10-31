"""Testes do efeito sonoro dos pop-ups (WAV sintetizado em memória)."""

import io
import sys
import wave

from sopro.core.audio.chime import DURATION_MS, SAMPLE_RATE_HZ, chime_wav


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
