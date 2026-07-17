"""Determinism: two `KnowledgeBaseEngine.execute()` calls over the same context
must produce the same checksum -- proving no random identity field leaked
into the checksummed payload (the recurring bug class caught in Phases 9-14).
"""

from app.knowledge_base.engine import KnowledgeBaseEngine


def test_two_runs_of_the_same_context_produce_the_same_checksum(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    result1 = engine.execute(entries, knowledge_configuration)
    result2 = engine.execute(entries, knowledge_configuration)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.knowledge_id != result2.metadata.knowledge_id


def test_statistics_are_identical_across_runs(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    result1 = engine.execute(entries, knowledge_configuration)
    result2 = engine.execute(entries, knowledge_configuration)
    assert result1.statistics == result2.statistics
    assert result1.entries == result2.entries


def test_entry_order_does_not_affect_checksum(entries, knowledge_configuration) -> None:
    engine = KnowledgeBaseEngine()
    result_forward = engine.execute(entries, knowledge_configuration)
    result_reversed = engine.execute(tuple(reversed(entries)), knowledge_configuration)
    assert result_forward.checksum == result_reversed.checksum
