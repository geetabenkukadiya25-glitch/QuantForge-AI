"""`ExtractionReport`: read-only, queryable presentation over an `ExtractionResult`."""

from app.ai_extraction.report import ExtractionReport
from app.ai_extraction.runner import ExtractionRunner


def test_indicators_table_has_one_row_per_mention(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    df = ExtractionReport(result).indicators_table()
    assert len(df) == len(result.indicators)


def test_entry_rules_table_has_one_row_per_mention(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    df = ExtractionReport(result).entry_rules_table()
    assert len(df) == len(result.entry_rules)


def test_statistics_matches_result_fields(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    stats = ExtractionReport(result).statistics()
    assert stats["strategy_name"] == result.strategy_name
    assert stats["checksum"] == result.checksum
    assert stats["indicator_count"] == len(result.indicators)


def test_executive_summary_mentions_strategy_name(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    summary = ExtractionReport(result).executive_summary()
    assert result.strategy_name in summary
    assert "confidence" in summary.lower()
