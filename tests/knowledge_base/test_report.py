"""`KnowledgeReport`: read-only, queryable presentation over a `KnowledgeResult`."""

from app.knowledge_base.models import KnowledgeCategory
from app.knowledge_base.report import KnowledgeReport
from app.knowledge_base.runner import KnowledgeRunner


def test_knowledge_report_has_one_row_per_entry(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    df = KnowledgeReport(result).knowledge_report()
    assert len(df) == len(result.entries)
    assert "title" in df.columns


def test_topic_report_resolves_related_entries(knowledge_context, entry_order_block, entry_fvg) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    topic = KnowledgeReport(result).topic_report(entry_order_block.entry_id)
    assert topic is not None
    assert topic.entry.entry_id == entry_order_block.entry_id
    assert entry_fvg.entry_id in {e.entry_id for e in topic.related_entries}


def test_topic_report_unknown_entry_returns_none(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    assert KnowledgeReport(result).topic_report("nonexistent") is None


def test_category_report_counts_and_lists_entry_ids(knowledge_context, entry_fvg) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    report = KnowledgeReport(result).category_report(KnowledgeCategory.FAIR_VALUE_GAPS)
    assert report.entry_count == 1
    assert entry_fvg.entry_id in report.entry_ids


def test_category_report_empty_category_returns_zero(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    report = KnowledgeReport(result).category_report(KnowledgeCategory.LIQUIDITY)
    assert report.entry_count == 0
    assert report.entry_ids == ()


def test_learning_progress_report_all_completed(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    all_ids = frozenset(e.entry_id for e in result.entries)
    progress = KnowledgeReport(result).learning_progress_report(all_ids)
    assert progress.completion_pct == 100.0
    assert progress.remaining_entry_ids == ()


def test_learning_progress_report_none_completed(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    progress = KnowledgeReport(result).learning_progress_report(frozenset())
    assert progress.completion_pct == 0.0
    assert progress.completed_entries == 0
    assert len(progress.remaining_entry_ids) == len(result.entries)


def test_learning_progress_report_partial(knowledge_context, entry_fvg) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    progress = KnowledgeReport(result).learning_progress_report(frozenset({entry_fvg.entry_id}))
    assert progress.completed_entries == 1
    assert 0.0 < progress.completion_pct < 100.0


def test_statistics_report_matches_result(knowledge_context) -> None:
    result = KnowledgeRunner().execute(knowledge_context)
    stats = KnowledgeReport(result).statistics_report()
    assert stats["total_entries"] == result.statistics.total_entries
