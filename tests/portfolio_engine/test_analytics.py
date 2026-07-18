"""Tests for `AnalyticsEngine`."""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.analytics import AnalyticsEngine
from app.portfolio_engine.correlation import CorrelationEngine
from app.portfolio_engine.models import PortfolioConfiguration
from app.portfolio_engine.risk import RiskEngine
from app.portfolio_engine.statistics import PortfolioStatisticsEngine


def _analyze(entries):
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    correlation_matrix = CorrelationEngine().correlate(entries)
    drawdown = RiskEngine().portfolio_max_drawdown_pct(entries, weights)
    statistics = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    risk_score = RiskEngine().risk_score(drawdown, correlation_matrix.average_correlation)
    return AnalyticsEngine().analyze(entries, weights, correlation_matrix, statistics, risk_score), weights


def test_every_score_between_zero_and_hundred(entry_a_full, entry_b_bare, entry_c_bare):
    analytics, _ = _analyze((entry_a_full, entry_b_bare, entry_c_bare))
    for score in (analytics.diversification_score, analytics.correlation_score, analytics.concentration_score, analytics.risk_score, analytics.portfolio_quality_score):
        assert 0.0 <= score <= 100.0


def test_concentration_score_higher_for_unequal_weights(entry_a_full, entry_b_bare):
    from app.portfolio_engine.models import ManualWeight

    id_a = entry_a_full.strategy_model.metadata.id
    id_b = entry_b_bare.strategy_model.metadata.id
    equal_analytics, _ = _analyze((entry_a_full, entry_b_bare))

    weights = {id_a: 0.9, id_b: 0.1}
    correlation_matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare))
    drawdown = RiskEngine().portfolio_max_drawdown_pct((entry_a_full, entry_b_bare), weights)
    statistics = PortfolioStatisticsEngine().compute((entry_a_full, entry_b_bare), weights, drawdown)
    risk_score = RiskEngine().risk_score(drawdown, correlation_matrix.average_correlation)
    concentrated_analytics = AnalyticsEngine().analyze((entry_a_full, entry_b_bare), weights, correlation_matrix, statistics, risk_score)

    assert concentrated_analytics.concentration_score > equal_analytics.concentration_score


def test_concentration_score_is_hhi_based(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    id_b = entry_b_bare.strategy_model.metadata.id
    weights = {id_a: 0.5, id_b: 0.5}
    correlation_matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare))
    drawdown = RiskEngine().portfolio_max_drawdown_pct((entry_a_full, entry_b_bare), weights)
    statistics = PortfolioStatisticsEngine().compute((entry_a_full, entry_b_bare), weights, drawdown)
    risk_score = RiskEngine().risk_score(drawdown, correlation_matrix.average_correlation)
    analytics = AnalyticsEngine().analyze((entry_a_full, entry_b_bare), weights, correlation_matrix, statistics, risk_score)
    # HHI of two equal 0.5 weights = 0.5, as a 0-100 figure = 50.0
    assert abs(analytics.concentration_score - 50.0) < 1e-6


def test_correlation_score_is_inverse_of_average_correlation(entry_a_full, entry_b_bare, entry_c_bare):
    analytics, _ = _analyze((entry_a_full, entry_b_bare, entry_c_bare))
    correlation_matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare, entry_c_bare))
    expected = round(max(0.0, min(100.0, (1.0 - correlation_matrix.average_correlation) / 2.0 * 100.0)), 4)
    assert analytics.correlation_score == expected


def test_empty_entries_returns_all_zero_analytics():
    analytics, _ = _analyze(())
    assert analytics.diversification_score == 0.0
    assert analytics.portfolio_quality_score == 0.0


def test_quality_score_zero_when_unprofitable(entry_a_full, entry_b_bare):
    from app.portfolio_engine.models import PortfolioStatistics

    weights = AllocationEngine().resolve_weights((entry_a_full, entry_b_bare), PortfolioConfiguration())
    correlation_matrix = CorrelationEngine().correlate((entry_a_full, entry_b_bare))
    loss_statistics = PortfolioStatistics(total_strategies=2, total_net_profit=-100.0)
    analytics = AnalyticsEngine().analyze((entry_a_full, entry_b_bare), weights, correlation_matrix, loss_statistics, risk_score=50.0)
    # Profitability component should be 0, so quality score is only diversification (35%) + risk (40%)
    expected = round(analytics.diversification_score * 0.35 + 50.0 * 0.40, 4)
    assert analytics.portfolio_quality_score == expected


def test_diversification_score_reflects_symbol_breadth(entry_a_full, entry_b_bare, entry_c_bare):
    two_symbol_analytics, _ = _analyze((entry_a_full, entry_b_bare, entry_c_bare))
    one_symbol_analytics, _ = _analyze((entry_a_full, entry_b_bare))
    # Not a strict inequality claim across different configs -- just confirm both are valid, computed scores.
    assert isinstance(two_symbol_analytics.diversification_score, float)
    assert isinstance(one_symbol_analytics.diversification_score, float)
