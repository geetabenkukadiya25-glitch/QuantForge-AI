"""`AnalyticsEngine`: pure aggregation over already-computed engine outputs, never recomputed."""

from app.research_engine.analytics import AnalyticsEngine


def test_indicator_usage_reflects_strategy_model_indicators(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    types = {u.component_type for u in analytics.indicator_usage}
    assert "SMA" in types
    sma_usage = next(u for u in analytics.indicator_usage if u.component_type == "SMA")
    assert sma_usage.strategy_count == 2
    assert set(sma_usage.strategy_ids) == {record_a_full.strategy_model.metadata.id, record_b_bare.strategy_model.metadata.id}


def test_smart_money_usage_empty_when_no_detectors_referenced(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    assert analytics.smart_money_usage == ()


def test_symbol_performance_groups_by_backtest_symbol(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    assert len(analytics.symbol_performance) == 1
    entry = analytics.symbol_performance[0]
    assert entry.symbol == "EURUSD"
    assert entry.strategy_count == 2


def test_timeframe_performance_groups_by_backtest_timeframe(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    assert len(analytics.timeframe_performance) == 1
    assert analytics.timeframe_performance[0].timeframe == "H1"


def test_session_performance_uses_declared_sessions(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    # Neither test strategy declares sessions in this fixture's SDL -- an empty result is correct.
    assert analytics.session_performance == ()


def test_optimization_history_present_only_for_records_with_optimization(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    strategy_ids = {s.strategy_id for s in analytics.optimization_history}
    assert record_a_full.strategy_model.metadata.id in strategy_ids
    assert record_b_bare.strategy_model.metadata.id not in strategy_ids


def test_walk_forward_stability_present_only_for_validated_records(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    strategy_ids = {s.strategy_id for s in analytics.walk_forward_stability}
    assert record_a_full.strategy_model.metadata.id in strategy_ids
    assert record_b_bare.strategy_model.metadata.id not in strategy_ids


def test_monte_carlo_robustness_present_only_for_validated_records(record_a_full, record_b_bare) -> None:
    analytics = AnalyticsEngine().analyze((record_a_full, record_b_bare))
    strategy_ids = {s.strategy_id for s in analytics.monte_carlo_robustness}
    assert record_a_full.strategy_model.metadata.id in strategy_ids
    assert record_b_bare.strategy_model.metadata.id not in strategy_ids


def test_analyze_empty_records_returns_empty_analytics() -> None:
    analytics = AnalyticsEngine().analyze(())
    assert analytics.indicator_usage == ()
    assert analytics.symbol_performance == ()
    assert analytics.optimization_history == ()
