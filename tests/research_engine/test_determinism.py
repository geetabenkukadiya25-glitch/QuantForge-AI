"""Determinism: two `ResearchEngine.execute()` calls over the same context must
produce the same checksum -- proving no random identity field leaked into
the checksummed payload (the recurring bug class caught in Phases 9-11).
"""

from app.research_engine.engine import ResearchEngine


def test_two_runs_of_the_same_context_produce_the_same_checksum(record_a_full, record_b_bare, research_configuration) -> None:
    engine = ResearchEngine()
    result1 = engine.execute((record_a_full, record_b_bare), research_configuration)
    result2 = engine.execute((record_a_full, record_b_bare), research_configuration)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.research_id != result2.metadata.research_id


def test_rankings_and_analytics_are_identical_across_runs(record_a_full, record_b_bare, research_configuration) -> None:
    engine = ResearchEngine()
    result1 = engine.execute((record_a_full, record_b_bare), research_configuration)
    result2 = engine.execute((record_a_full, record_b_bare), research_configuration)
    assert result1.rankings == result2.rankings
    assert result1.analytics == result2.analytics
    assert result1.executive_summary == result2.executive_summary


def test_record_order_does_not_affect_checksum(record_a_full, record_b_bare, research_configuration) -> None:
    """Both statistics and rankings are internally sorted (by strategy_id /
    ranking metric), so the checksum shouldn't depend on the order records
    were supplied in."""
    engine = ResearchEngine()
    result_forward = engine.execute((record_a_full, record_b_bare), research_configuration)
    result_reversed = engine.execute((record_b_bare, record_a_full), research_configuration)
    assert result_forward.checksum == result_reversed.checksum
