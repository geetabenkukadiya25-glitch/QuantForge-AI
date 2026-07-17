"""`KnowledgeStatisticsEngine`: pure aggregation over a tuple of `KnowledgeEntry`."""

from app.knowledge_base.models import DifficultyLevel, KnowledgeCategory
from app.knowledge_base.statistics import KnowledgeStatisticsEngine
from tests.knowledge_base.conftest import make_entry


def test_total_entries_and_categories(entries) -> None:
    stats = KnowledgeStatisticsEngine().compute(entries)
    assert stats.total_entries == 3
    assert stats.total_categories == 3  # FVG, ORDER_BLOCKS, RISK_MANAGEMENT


def test_entries_by_category_counts(entries) -> None:
    stats = KnowledgeStatisticsEngine().compute(entries)
    by_category = {c.category: c.entry_count for c in stats.entries_by_category}
    assert by_category[KnowledgeCategory.FAIR_VALUE_GAPS] == 1
    assert by_category[KnowledgeCategory.ORDER_BLOCKS] == 1


def test_entries_by_difficulty_counts(entries) -> None:
    stats = KnowledgeStatisticsEngine().compute(entries)
    by_difficulty = {d.difficulty: d.entry_count for d in stats.entries_by_difficulty}
    assert by_difficulty[DifficultyLevel.BEGINNER] == 1
    assert by_difficulty[DifficultyLevel.INTERMEDIATE] == 1
    assert by_difficulty[DifficultyLevel.ADVANCED] == 1


def test_top_tags_sorted_by_frequency() -> None:
    entries = (
        make_entry("a", tags=("smc", "structure")),
        make_entry("b", tags=("smc",)),
        make_entry("c", tags=("smc", "risk")),
    )
    stats = KnowledgeStatisticsEngine().compute(entries)
    assert stats.top_tags[0].tag == "smc"
    assert stats.top_tags[0].entry_count == 3


def test_average_content_length(entries) -> None:
    stats = KnowledgeStatisticsEngine().compute(entries)
    expected = sum(len(e.content) for e in entries) / len(entries)
    assert stats.average_content_length == round(expected, 4)


def test_total_cross_references_sums_related_entry_ids(entries) -> None:
    stats = KnowledgeStatisticsEngine().compute(entries)
    assert stats.total_cross_references == 1  # only entry_order_block references entry_fvg


def test_empty_entries_produces_zeroed_statistics() -> None:
    stats = KnowledgeStatisticsEngine().compute(())
    assert stats.total_entries == 0
    assert stats.total_categories == 0
    assert stats.average_content_length == 0.0
    assert stats.entries_by_category == ()
