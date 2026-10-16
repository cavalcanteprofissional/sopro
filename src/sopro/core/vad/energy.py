"""Segmentação de fala por energia (RMS) sobre PCM 16-bit mono (docs/02 §5).

Algoritmo determinístico e sem dependências externas:

1. divide o sinal em quadros de ``frame_ms``;
2. calcula o RMS de cada quadro e marca como fala quando atinge
   ``energy_threshold``;
3. funde trechos separados por silêncio menor que ``min_silence_ms``;
4. descarta trechos menores que ``min_speech_ms``;
5. aplica ``pad_ms`` de folga nas bordas;
6. divide trechos longos em blocos de ``max_segment_ms`` com ``overlap_ms``.

A entrada é PCM assinado de 16 bits, little-endian, mono.
"""

from __future__ import annotations

import array
import math
import sys

from sopro.core.vad.segmenter import SpeechSegment, VadConfig

_INT16_SCALE = 32768.0


def _to_samples(pcm: bytes) -> array.array:
    usable = pcm[: len(pcm) - (len(pcm) % 2)]
    samples = array.array("h")
    samples.frombytes(usable)
    if sys.byteorder == "big":
        samples.byteswap()
    return samples


def _to_bytes(samples: array.array) -> bytes:
    if sys.byteorder == "big":
        samples = array.array("h", samples)
        samples.byteswap()
    return samples.tobytes()


def _frame_rms(samples: array.array, start: int, end: int) -> float:
    if end <= start:
        return 0.0
    total = 0.0
    for index in range(start, end):
        value = samples[index] / _INT16_SCALE
        total += value * value
    return math.sqrt(total / (end - start))


def _speech_runs(flags: list[bool]) -> list[list[int]]:
    runs: list[list[int]] = []
    start: int | None = None
    for index, is_speech in enumerate(flags):
        if is_speech and start is None:
            start = index
        elif not is_speech and start is not None:
            runs.append([start, index])
            start = None
    if start is not None:
        runs.append([start, len(flags)])
    return runs


def _merge_runs(runs: list[list[int]], min_silence_frames: int) -> list[list[int]]:
    if not runs:
        return []
    merged = [list(runs[0])]
    for start, end in runs[1:]:
        if start - merged[-1][1] < min_silence_frames:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged


def _split_segment(
    samples: array.array,
    start_frame: int,
    end_frame: int,
    frame_len: int,
    config: VadConfig,
) -> list[SpeechSegment]:
    max_frames = max(1, round(config.max_segment_ms / config.frame_ms))
    overlap_frames = min(round(config.overlap_ms / config.frame_ms), max_frames - 1)
    step = max(1, max_frames - overlap_frames)

    segments: list[SpeechSegment] = []
    index = start_frame
    while index < end_frame:
        stop = min(index + max_frames, end_frame)
        start_sample = index * frame_len
        end_sample = stop * frame_len
        segments.append(
            SpeechSegment(
                start_ms=start_sample * 1000 // config.sample_rate,
                end_ms=end_sample * 1000 // config.sample_rate,
                pcm=_to_bytes(samples[start_sample:end_sample]),
            )
        )
        if stop >= end_frame:
            break
        index += step
    return segments


def segment(pcm: bytes, config: VadConfig | None = None) -> list[SpeechSegment]:
    """Segmenta PCM 16-bit mono em trechos de fala (docs/02 §5)."""
    config = config or VadConfig()
    samples = _to_samples(pcm)
    frame_len = max(1, round(config.sample_rate * config.frame_ms / 1000))
    total_frames = len(samples) // frame_len
    if total_frames == 0:
        return []

    flags = [
        _frame_rms(samples, i * frame_len, (i + 1) * frame_len) >= config.energy_threshold
        for i in range(total_frames)
    ]

    min_speech_frames = max(1, math.ceil(config.min_speech_ms / config.frame_ms))
    min_silence_frames = max(1, math.ceil(config.min_silence_ms / config.frame_ms))
    pad_frames = round(config.pad_ms / config.frame_ms)

    runs = _merge_runs(_speech_runs(flags), min_silence_frames)

    segments: list[SpeechSegment] = []
    for start, end in runs:
        if end - start < min_speech_frames:
            continue
        start = max(0, start - pad_frames)
        end = min(total_frames, end + pad_frames)
        segments.extend(_split_segment(samples, start, end, frame_len, config))
    return segments
