"""Tests for `RiskEngine`: risk contribution, portfolio drawdown, and risk score."""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.models import PortfolioConfiguration
from app.portfolio_engine.risk import RiskEngine


def test_risk_contribution_sums_to_one_hundred(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    contribution = RiskEngine().risk_contribution_pct(entries, weights)
    assert abs(sum(contribution.values()) - 100.0) < 1e-4


def test_risk_contribution_empty_entries_returns_empty_dict():
    assert RiskEngine().risk_contribution_pct((), {}) == {}


def test_portfolio_max_drawdown_is_weighted_average(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    drawdown = RiskEngine().portfolio_max_drawdown_pct(entries, weights)
    individual = [e.backtest_result.drawdown_report.max_drawdown_pct for e in entries]
    assert min(individual) - 1e-6 <= drawdown <= max(individual) + 1e-6


def test_portfolio_max_drawdown_empty_is_zero():
    assert RiskEngine().portfolio_max_drawdown_pct((), {}) == 0.0


def test_risk_score_is_between_zero_and_hundred():
    score = RiskEngine().risk_score(portfolio_max_drawdown_pct=15.0, average_correlation=0.2)
    assert 0.0 <= score <= 100.0


def test_risk_score_lower_drawdown_scores_higher():
    low_dd = RiskEngine().risk_score(portfolio_max_drawdown_pct=5.0, average_correlation=0.0)
    high_dd = RiskEngine().risk_score(portfolio_max_drawdown_pct=50.0, average_correlation=0.0)
    assert low_dd > high_dd


def test_risk_score_negative_correlation_scores_higher_than_positive():
    diversified = RiskEngine().risk_score(portfolio_max_drawdown_pct=10.0, average_correlation=-0.5)
    correlated = RiskEngine().risk_score(portfolio_max_drawdown_pct=10.0, average_correlation=0.9)
    assert diversified > correlated


def test_risk_score_extreme_drawdown_clips_to_zero_floor():
    score = RiskEngine().risk_score(portfolio_max_drawdown_pct=1000.0, average_correlation=1.0)
    assert score >= 0.0
