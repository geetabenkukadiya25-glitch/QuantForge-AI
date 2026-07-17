"""`RecommendationEngine`: text-only, rule-based guidance over a completed ranking."""

from app.research_engine.models import (
    ComparisonStatistics,
    InstitutionalQualityScore,
    RankingEntry,
    RecommendationPriority,
    ResearchConfidenceScore,
    StrategyInsights,
    StrategyScore,
)
from app.research_engine.recommendations import RecommendationEngine


def _entry(strategy_id: str, rank: int, has_validation: bool, has_sufficient_trades: bool, institutional: bool, consecutive_losses: int = 0) -> RankingEntry:
    stats = ComparisonStatistics(strategy_id=strategy_id, max_drawdown_pct=10.0, consecutive_losses=consecutive_losses)
    strategy_score = StrategyScore(strategy_id=strategy_id, score=50, profitability_component=50, risk_component=50, consistency_component=50)
    confidence_score = ResearchConfidenceScore(strategy_id=strategy_id, score=50, has_validation=has_validation, has_sufficient_trades=has_sufficient_trades)
    institutional_score = InstitutionalQualityScore(strategy_id=strategy_id, score=80 if institutional else 20, is_institutional_grade=institutional)
    return RankingEntry(
        rank=rank, strategy_id=strategy_id, strategy_name=strategy_id.title(),
        strategy_score=strategy_score, confidence_score=confidence_score, institutional_quality_score=institutional_score, statistics=stats,
    )


def test_top_ranked_gets_a_high_priority_recommendation() -> None:
    entries = (_entry("a", 1, True, True, True), _entry("b", 2, True, True, True))
    recs = RecommendationEngine().generate(entries, {})
    top_recs = [r for r in recs if r.strategy_id == "a" and r.priority == RecommendationPriority.HIGH]
    assert any("#1" in r.message for r in top_recs)


def test_missing_validation_produces_high_priority_recommendation() -> None:
    entries = (_entry("a", 1, False, True, True),)
    recs = RecommendationEngine().generate(entries, {"a": StrategyInsights(strategy_id="a")})
    assert any(r.strategy_id == "a" and r.priority == RecommendationPriority.HIGH and "validation" in r.message.lower() for r in recs)


def test_insufficient_trades_produces_medium_priority_recommendation() -> None:
    entries = (_entry("a", 1, True, False, True),)
    recs = RecommendationEngine().generate(entries, {"a": StrategyInsights(strategy_id="a")})
    assert any(r.strategy_id == "a" and r.priority == RecommendationPriority.MEDIUM for r in recs)


def test_long_losing_streak_produces_low_priority_recommendation() -> None:
    entries = (_entry("a", 1, True, True, True, consecutive_losses=6),)
    recs = RecommendationEngine().generate(entries, {"a": StrategyInsights(strategy_id="a")})
    assert any(r.strategy_id == "a" and r.priority == RecommendationPriority.LOW and "losses" in r.message.lower() for r in recs)


def test_no_institutional_grade_strategies_triggers_portfolio_recommendation() -> None:
    entries = (_entry("a", 1, True, True, False), _entry("b", 2, True, True, False))
    recs = RecommendationEngine().generate(entries, {"a": StrategyInsights(strategy_id="a"), "b": StrategyInsights(strategy_id="b")})
    assert any(r.strategy_id is None and "institutional-grade" in r.message.lower() for r in recs)


def test_empty_rankings_produces_no_recommendations() -> None:
    assert RecommendationEngine().generate((), {}) == ()


def test_missing_insights_entry_is_skipped_gracefully() -> None:
    entries = (_entry("a", 1, True, True, True),)
    recs = RecommendationEngine().generate(entries, {})  # no insights for "a"
    assert isinstance(recs, tuple)
