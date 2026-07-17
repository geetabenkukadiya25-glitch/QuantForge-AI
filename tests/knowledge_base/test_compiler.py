"""`KnowledgeCompiler`: deterministic checksum excludes identity/timestamp fields."""

from app.knowledge_base.compiler import KnowledgeCompiler
from app.knowledge_base.statistics import KnowledgeStatisticsEngine


def test_compile_produces_a_valid_result(knowledge_context) -> None:
    statistics = KnowledgeStatisticsEngine().compute(knowledge_context.entries)
    result = KnowledgeCompiler().compile(knowledge_context, statistics)
    assert result.checksum
    assert result.result_id
    assert result.metadata.entry_count == len(knowledge_context.entries)


def test_same_context_produces_the_same_checksum(knowledge_context) -> None:
    statistics = KnowledgeStatisticsEngine().compute(knowledge_context.entries)
    result1 = KnowledgeCompiler().compile(knowledge_context, statistics)
    result2 = KnowledgeCompiler().compile(knowledge_context, statistics)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.knowledge_id != result2.metadata.knowledge_id


def test_entry_order_does_not_affect_checksum(entries, knowledge_configuration) -> None:
    from app.knowledge_base.context import KnowledgeContext

    forward = KnowledgeContext(entries=entries, configuration=knowledge_configuration)
    reversed_context = KnowledgeContext(entries=tuple(reversed(entries)), configuration=knowledge_configuration)

    stats_forward = KnowledgeStatisticsEngine().compute(forward.entries)
    stats_reversed = KnowledgeStatisticsEngine().compute(reversed_context.entries)

    result_forward = KnowledgeCompiler().compile(forward, stats_forward)
    result_reversed = KnowledgeCompiler().compile(reversed_context, stats_reversed)
    assert result_forward.checksum == result_reversed.checksum


def test_different_content_produces_a_different_checksum(entry_fvg, knowledge_configuration) -> None:
    from app.knowledge_base.context import KnowledgeContext

    context_a = KnowledgeContext(entries=(entry_fvg,), configuration=knowledge_configuration)
    other_entry = entry_fvg.model_copy(update={"content": "Completely different content."})
    context_b = KnowledgeContext(entries=(other_entry,), configuration=knowledge_configuration)

    stats_a = KnowledgeStatisticsEngine().compute(context_a.entries)
    stats_b = KnowledgeStatisticsEngine().compute(context_b.entries)
    result_a = KnowledgeCompiler().compile(context_a, stats_a)
    result_b = KnowledgeCompiler().compile(context_b, stats_b)
    assert result_a.checksum != result_b.checksum
