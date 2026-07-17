"""`InsightsEngine`: rule-based strengths/weaknesses/warnings over already-computed scores."""

from app.research_engine.insights import InsightsEngine
from app.research_engine.models import ComparisonStatistics, ResearchConfiguration
from app.research_engine.ranking import ScoringEngine


def _run(record, **stat_overrides):
    base = dict(strategy_id=record.strategy_model.metadata.id, total_trades=50, expectancy=1.0, profit_factor=1.6, win_rate=55.0, max_drawdown_pct=10.0, sharpe_ratio=1.1, consecutive_losses=1)
    base.update(stat_overrides)
    stats = ComparisonStatistics(**base)
    config = ResearchConfiguration(min_trades_for_confidence=30, max_acceptable_drawdown_pct=20.0)
    engine = ScoringEngine()
    strategy_score = engine.strategy_score(stats)
    confidence_score = engine.confidence_score(record, stats, config)
    institutional_score = engine.institutional_quality_score(stats, strategy_score, confidence_score, config)
    insights = InsightsEngine().derive(record, stats, strategy_score, confidence_score, institutional_score, config)
    return insights


def test_positive_expectancy_is_a_strength(record_b_bare) -> None:
    insights = _run(record_b_bare, expectancy=5.0)
    assert any("expectancy" in s.lower() for s in insights.strengths)


def test_negative_expectancy_is_a_weakness(record_b_bare) -> None:
    insights = _run(record_b_bare, expectancy=-5.0)
    assert any("expectancy" in w.lower() for w in insights.weaknesses)


def test_high_drawdown_is_a_weakness(record_b_bare) -> None:
    insights = _run(record_b_bare, max_drawdown_pct=90.0)
    assert any("drawdown" in w.lower() for w in insights.weaknesses)


def test_long_losing_streak_is_a_weakness(record_b_bare) -> None:
    insights = _run(record_b_bare, consecutive_losses=8)
    assert any("losing streak" in w.lower() for w in insights.weaknesses)


def test_insufficient_trades_produces_warning(record_b_bare) -> None:
    insights = _run(record_b_bare, total_trades=2)
    assert any("trade" in w.lower() for w in insights.warnings)


def test_missing_validation_produces_warning(record_b_bare) -> None:
    insights = _run(record_b_bare)
    assert any("validated" in w.lower() for w in insights.warnings)


def test_present_validation_omits_validation_warning(record_a_full) -> None:
    insights = _run(record_a_full, total_trades=record_a_full.backtest_result.statistics.total_trades or 50)
    assert not any("not yet validated" in w.lower() for w in insights.warnings)


def test_missing_optimization_produces_warning(record_b_bare) -> None:
    insights = _run(record_b_bare)
    assert any("optimized" in w.lower() for w in insights.warnings)


def test_present_optimization_omits_optimization_warning(record_a_full) -> None:
    insights = _run(record_a_full, total_trades=record_a_full.backtest_result.statistics.total_trades or 50)
    assert not any("not yet optimized" in w.lower() for w in insights.warnings)
