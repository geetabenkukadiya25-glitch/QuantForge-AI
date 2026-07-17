"""Frozen/immutable, hashable, versioned model behavior for research_engine models."""

import pytest
from pydantic import ValidationError

from app.research_engine.metadata import RESEARCH_RESULT_VERSION, ResearchMetadata
from app.research_engine.models import (
    ComparisonStatistics,
    ExecutiveSummary,
    InstitutionalQualityScore,
    RankingMetric,
    Recommendation,
    RecommendationPriority,
    ResearchAnalytics,
    ResearchConfidenceScore,
    ResearchConfiguration,
    StrategyInsights,
    StrategyScore,
)


def test_research_configuration_is_frozen_and_hashable() -> None:
    config = ResearchConfiguration()
    with pytest.raises(ValidationError):
        config.ranking_metric = RankingMetric.NET_PROFIT
    hash(config)


def test_research_configuration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ResearchConfiguration(bogus_field=True)


def test_research_configuration_defaults() -> None:
    config = ResearchConfiguration()
    assert config.ranking_metric == RankingMetric.INSTITUTIONAL_QUALITY_SCORE
    assert config.min_trades_for_confidence == 30
    assert config.max_acceptable_drawdown_pct == 30.0
    assert config.institutional_min_score == 70.0


def test_comparison_statistics_is_frozen_and_hashable() -> None:
    stats = ComparisonStatistics(strategy_id="s1")
    with pytest.raises(ValidationError):
        stats.net_profit = 100.0
    hash(stats)


def test_strategy_score_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        StrategyScore(strategy_id="s1", score=101, profitability_component=0, risk_component=0, consistency_component=0)


def test_research_confidence_score_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        ResearchConfidenceScore(strategy_id="s1", score=-1, has_validation=False, has_sufficient_trades=False)


def test_institutional_quality_score_carries_criteria() -> None:
    score = InstitutionalQualityScore(strategy_id="s1", score=80, is_institutional_grade=True, criteria_met=("A",), criteria_failed=())
    assert score.criteria_met == ("A",)
    hash(score)


def test_recommendation_priority_values() -> None:
    assert {p.value for p in RecommendationPriority} == {"HIGH", "MEDIUM", "LOW"}


def test_recommendation_allows_none_strategy_id() -> None:
    rec = Recommendation(strategy_id=None, priority=RecommendationPriority.LOW, message="test")
    assert rec.strategy_id is None


def test_strategy_insights_defaults_to_empty_tuples() -> None:
    insights = StrategyInsights(strategy_id="s1")
    assert insights.strengths == ()
    assert insights.weaknesses == ()
    assert insights.warnings == ()


def test_executive_summary_defaults() -> None:
    summary = ExecutiveSummary(total_strategies_analyzed=0, average_institutional_quality_score=0.0)
    assert summary.top_strategy_id is None
    assert summary.institutional_grade_count == 0


def test_research_analytics_defaults_to_empty_tuples() -> None:
    analytics = ResearchAnalytics()
    assert analytics.indicator_usage == ()
    assert analytics.symbol_performance == ()


def test_research_metadata_default_version() -> None:
    metadata = ResearchMetadata(research_id="r1", strategy_ids=("s1",), strategy_checksums=("c1",), backtest_result_ids=("b1",))
    assert metadata.result_version == RESEARCH_RESULT_VERSION


def test_research_metadata_requires_at_least_one_strategy_id() -> None:
    with pytest.raises(ValidationError):
        ResearchMetadata(research_id="r1", strategy_ids=(), strategy_checksums=(), backtest_result_ids=())


def test_ranking_metric_values() -> None:
    expected = {"STRATEGY_SCORE", "INSTITUTIONAL_QUALITY_SCORE", "NET_PROFIT", "PROFIT_FACTOR", "SHARPE_RATIO", "CONFIDENCE_SCORE"}
    assert {m.value for m in RankingMetric} == expected
