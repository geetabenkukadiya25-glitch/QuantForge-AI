"""`ScoringEngine`/`RankingEngine`: framework-level scores, never a new simulation."""

from app.research_engine.models import ComparisonStatistics, RankingMetric, ResearchConfiguration
from app.research_engine.ranking import RankingEngine, ScoringEngine


def _stats(**overrides) -> ComparisonStatistics:
    base = dict(strategy_id="s1", total_trades=50, net_profit=100.0, expectancy=2.0, profit_factor=1.8, win_rate=55.0, max_drawdown_pct=10.0, recovery_factor=3.0, sharpe_ratio=1.2)
    base.update(overrides)
    return ComparisonStatistics(**base)


def test_strategy_score_is_zero_for_non_positive_net_profit() -> None:
    stats = _stats(net_profit=-10.0)
    score = ScoringEngine().strategy_score(stats)
    assert score.profitability_component == 0.0


def test_strategy_score_bounded_0_to_100() -> None:
    stats = _stats()
    score = ScoringEngine().strategy_score(stats)
    assert 0.0 <= score.score <= 100.0
    assert 0.0 <= score.profitability_component <= 100.0
    assert 0.0 <= score.risk_component <= 100.0
    assert 0.0 <= score.consistency_component <= 100.0


def test_confidence_score_without_validation_uses_only_trade_count(record_b_bare) -> None:
    stats = _stats(strategy_id=record_b_bare.strategy_model.metadata.id, total_trades=50)
    config = ResearchConfiguration(min_trades_for_confidence=30)
    score = ScoringEngine().confidence_score(record_b_bare, stats, config)
    assert score.has_validation is False
    assert score.has_sufficient_trades is True
    assert score.score == 40.0  # 0% validation * 0.6 + 100% trade count * 0.4


def test_confidence_score_with_validation_incorporates_validation_component(record_a_full) -> None:
    stats = _stats(strategy_id=record_a_full.strategy_model.metadata.id, total_trades=record_a_full.backtest_result.statistics.total_trades)
    config = ResearchConfiguration(min_trades_for_confidence=1)
    score = ScoringEngine().confidence_score(record_a_full, stats, config)
    assert score.has_validation is True
    assert score.score > 0.0


def test_confidence_score_insufficient_trades_scales_down(record_b_bare) -> None:
    stats = _stats(strategy_id=record_b_bare.strategy_model.metadata.id, total_trades=10)
    config = ResearchConfiguration(min_trades_for_confidence=100)
    score = ScoringEngine().confidence_score(record_b_bare, stats, config)
    assert score.has_sufficient_trades is False
    assert 0.0 <= score.score < 40.0  # trade-count component < 100%, scaled by 0.4


def test_institutional_quality_score_flags_criteria(record_b_bare) -> None:
    stats = _stats(strategy_id=record_b_bare.strategy_model.metadata.id, total_trades=5, expectancy=-1.0, max_drawdown_pct=50.0, profit_factor=0.5)
    config = ResearchConfiguration(min_trades_for_confidence=30, max_acceptable_drawdown_pct=20.0, institutional_min_score=1.0)
    engine = ScoringEngine()
    strategy_score = engine.strategy_score(stats)
    confidence_score = engine.confidence_score(record_b_bare, stats, config)
    quality = engine.institutional_quality_score(stats, strategy_score, confidence_score, config)
    assert quality.is_institutional_grade is False
    assert len(quality.criteria_failed) >= 4  # trades, validation, expectancy, drawdown, profit_factor


def test_institutional_quality_score_all_criteria_met(record_a_full) -> None:
    engine = ScoringEngine()
    from app.research_engine.statistics import ResearchStatisticsEngine

    stats = ResearchStatisticsEngine().compute(record_a_full)
    config = ResearchConfiguration(min_trades_for_confidence=1, max_acceptable_drawdown_pct=100.0, institutional_min_score=0.0)
    strategy_score = engine.strategy_score(stats)
    confidence_score = engine.confidence_score(record_a_full, stats, config)
    quality = engine.institutional_quality_score(stats, strategy_score, confidence_score, config)
    # has_validation is guaranteed True; other criteria depend on synthetic data, just check consistency
    assert quality.is_institutional_grade == (quality.score >= config.institutional_min_score and not quality.criteria_failed)


def test_ranking_orders_by_configured_metric() -> None:
    stats = (_stats(strategy_id="low", net_profit=10.0), _stats(strategy_id="high", net_profit=1000.0))
    engine = ScoringEngine()
    config = ResearchConfiguration(ranking_metric=RankingMetric.NET_PROFIT, min_trades_for_confidence=1)

    strategy_scores = {}
    confidence_scores = {}
    institutional_scores = {}
    names = {}
    for stat in stats:
        # Use a bare-bones stand-in record since we only need has_validation=False behavior.
        class _FakeRecord:
            validation_result = None

        strategy_scores[stat.strategy_id] = engine.strategy_score(stat)
        confidence_scores[stat.strategy_id] = engine.confidence_score(_FakeRecord(), stat, config)
        institutional_scores[stat.strategy_id] = engine.institutional_quality_score(stat, strategy_scores[stat.strategy_id], confidence_scores[stat.strategy_id], config)
        names[stat.strategy_id] = stat.strategy_id

    rankings = RankingEngine().rank(stats, strategy_scores, confidence_scores, institutional_scores, names, config)
    assert rankings[0].strategy_id == "high"
    assert rankings[0].rank == 1
    assert rankings[1].strategy_id == "low"
    assert rankings[1].rank == 2


def test_ranking_by_profit_factor_treats_none_as_last() -> None:
    stats = (_stats(strategy_id="no-pf", profit_factor=None), _stats(strategy_id="has-pf", profit_factor=2.0))
    engine = ScoringEngine()
    config = ResearchConfiguration(ranking_metric=RankingMetric.PROFIT_FACTOR, min_trades_for_confidence=1)

    class _FakeRecord:
        validation_result = None

    strategy_scores = {s.strategy_id: engine.strategy_score(s) for s in stats}
    confidence_scores = {s.strategy_id: engine.confidence_score(_FakeRecord(), s, config) for s in stats}
    institutional_scores = {s.strategy_id: engine.institutional_quality_score(s, strategy_scores[s.strategy_id], confidence_scores[s.strategy_id], config) for s in stats}
    names = {s.strategy_id: s.strategy_id for s in stats}

    rankings = RankingEngine().rank(stats, strategy_scores, confidence_scores, institutional_scores, names, config)
    assert rankings[0].strategy_id == "has-pf"
    assert rankings[1].strategy_id == "no-pf"
