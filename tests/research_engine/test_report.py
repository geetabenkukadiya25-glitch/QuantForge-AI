"""`ResearchReport`: read-only, queryable presentation over a `ResearchResult`."""

from app.research_engine.report import ResearchReport
from app.research_engine.runner import ResearchRunner


def test_comparison_table_has_one_row_per_strategy(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    df = ResearchReport(result).comparison_table()
    assert len(df) == len(result.statistics)
    assert "net_profit" in df.columns


def test_rankings_table_has_one_row_per_ranking_entry(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    df = ResearchReport(result).rankings_table()
    assert len(df) == len(result.rankings)
    assert "institutional_quality_score" in df.columns


def test_indicator_usage_table_reflects_analytics(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    df = ResearchReport(result).indicator_usage_table()
    assert len(df) == len(result.analytics.indicator_usage)


def test_symbol_performance_table_reflects_analytics(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    df = ResearchReport(result).symbol_performance_table()
    assert len(df) == len(result.analytics.symbol_performance)


def test_recommendations_table_reflects_recommendations(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    df = ResearchReport(result).recommendations_table()
    assert len(df) == len(result.recommendations)


def test_insights_for_returns_matching_strategy(research_context, record_a_full) -> None:
    result = ResearchRunner().execute(research_context)
    insights = ResearchReport(result).insights_for(record_a_full.strategy_model.metadata.id)
    assert insights["strategy_id"] == record_a_full.strategy_model.metadata.id


def test_insights_for_unknown_strategy_returns_empty_dict(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    assert ResearchReport(result).insights_for("nonexistent") == {}


def test_executive_summary_matches_result(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    summary = ResearchReport(result).executive_summary()
    assert summary["total_strategies_analyzed"] == result.executive_summary.total_strategies_analyzed
