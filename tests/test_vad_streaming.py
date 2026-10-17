"""Testes da segmentação incremental (sopro.core.vad.streaming)."""

import array

from sopro.core.vad import StreamingSegmenter, VadConfig


def _tone(ms: int, rate: int = 16000, freq: int = 440, amp: int = 8000) -> bytes:
    samples = array.array("h")
    total = rate * ms // 1000
    period = max(2, rate // freq)
    for i in range(total):
        samples.append(amp if (i % period) < (period // 2) else -amp)
    return samples.tobytes()


def _silence(ms: int, rate: int = 16000) -> bytes:
    return bytes(rate * ms // 1000 * 2)


def test_speech_then_silence_emits_segment():
    segmenter = StreamingSegmenter()

    segments = segmenter.feed(_tone(500) + _silence(400))

    assert len(segments) == 1
    assert segments[0].start_ms == 0
    assert 700 <= segments[0].end_ms <= 900
    assert segments[0].pcm


def test_all_silence_emits_nothing():
    segmenter = StreamingSegmenter()

    assert segmenter.feed(_silence(2000)) == []


def test_short_burst_is_dropped():
    segmenter = StreamingSegmenter()

    segments = segmenter.feed(_tone(90) + _silence(500))

    assert segments == []


def test_long_speech_splits_into_blocks():
    config = VadConfig(max_segment_ms=300, overlap_ms=60, min_speech_ms=250)
    segmenter = StreamingSegmenter(config)

    segments = segmenter.feed(_tone(1000))

    assert len(segments) >= 3
    starts = [s.start_ms for s in segments]
    assert starts == sorted(starts)
    for segment in segments:
        assert segment.duration_ms <= config.max_segment_ms + config.frame_ms


def test_feed_chunks_equivalent_to_single_feed():
    single = StreamingSegmenter().feed(_tone(500) + _silence(400))

    segmented = StreamingSegmenter()
    stream = _tone(500) + _silence(400)
    out = []
    for i in range(0, len(stream), 7):
        out.extend(segmented.feed(stream[i : i + 7]))

    assert [s.start_ms for s in out] == [s.start_ms for s in single]
    assert [s.end_ms for s in out] == [s.end_ms for s in single]


def test_flush_emits_pending_segment():
    segmenter = StreamingSegmenter()

    assert segmenter.feed(_tone(600)) == []
    flushed = segmenter.flush()

    assert len(flushed) == 1
    assert flushed[0].start_ms == 0
    assert segmenter.flush() == []


def test_reset_clears_state():
    segmenter = StreamingSegmenter()
    segmenter.feed(_tone(500))

    segmenter.reset()

    assert segmenter.flush() == []
