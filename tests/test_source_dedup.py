"""Testes da deduplicação entre áudio do sistema e microfone."""

from sopro.app.source_dedup import SourceDeduplicator


class Clock:
    def __init__(self) -> None:
        self.now = 10.0

    def __call__(self) -> float:
        return self.now


def test_same_transcript_from_other_source_is_duplicate():
    clock = Clock()
    dedup = SourceDeduplicator(window_s=2.0, clock=clock)

    assert dedup.duplicate_transcript("mic", "The Transformer model") is False
    assert dedup.duplicate_transcript("system", "the transformer model") is True
    assert dedup.duplicate_transcript("mic", "the transformer model") is False


def test_duplicate_window_expires():
    clock = Clock()
    dedup = SourceDeduplicator(window_s=2.0, clock=clock)

    assert dedup.duplicate_transcript("mic", "transformer") is False
    clock.now += 2.1
    assert dedup.duplicate_transcript("system", "transformer") is False


def test_terms_are_deduplicated_only_across_sources():
    clock = Clock()
    dedup = SourceDeduplicator(window_s=2.0, clock=clock)

    assert dedup.duplicate_term("mic", "Transformer") is False
    assert dedup.duplicate_term("mic", "transformer") is False
    assert dedup.duplicate_term("system", "transformer") is True


def test_reset_clears_history():
    dedup = SourceDeduplicator()
    dedup.duplicate_transcript("mic", "sopro")
    dedup.duplicate_term("mic", "sopro")
    dedup.reset()
    assert dedup.duplicate_transcript("system", "sopro") is False
    assert dedup.duplicate_term("system", "sopro") is False
