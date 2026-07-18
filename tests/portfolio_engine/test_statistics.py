"""Tests for `PortfolioStatisticsEngine`."""

from app.portfolio_engine.allocation import AllocationEngine
from app.portfolio_engine.models import PortfolioConfiguration
from app.portfolio_engine.risk import RiskEngine
from app.portfolio_engine.statistics import PortfolioStatisticsEngine


def _weights_and_drawdown(entries):
    weights = AllocationEngine().resolve_weights(entries, PortfolioConfiguration())
    drawdown = RiskEngine().portfolio_max_drawdown_pct(entries, weights)
    return weights, drawdown


def test_total_net_profit_is_sum_of_members(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    expected = round(entry_a_full.backtest_result.statistics.net_profit + entry_b_bare.backtest_result.statistics.net_profit, 4)
    assert stats.total_net_profit == expected


def test_total_strategies_matches_entry_count(entry_a_full, entry_b_bare, entry_c_bare):
    entries = (entry_a_full, entry_b_bare, entry_c_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    assert stats.total_strategies == 3


def test_combined_total_trades_is_sum_of_members(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    expected = entry_a_full.backtest_result.statistics.total_trades + entry_b_bare.backtest_result.statistics.total_trades
    assert stats.combined_total_trades == expected


def test_portfolio_win_rate_is_weighted_average(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    win_rates = [e.backtest_result.statistics.win_rate for e in entries]
    assert min(win_rates) - 1e-6 <= stats.portfolio_win_rate <= max(win_rates) + 1e-6


def test_empty_entries_returns_zeroed_statistics():
    stats = PortfolioStatisticsEngine().compute((), {}, 0.0)
    assert stats.total_strategies == 0
    assert stats.total_net_profit == 0.0


def test_average_return_pct_uses_initial_balance(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    assert isinstance(stats.average_return_pct, float)


def test_portfolio_max_drawdown_pct_passthrough(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    assert stats.portfolio_max_drawdown_pct == drawdown


def test_sharpe_sortino_calmar_are_none_or_float(entry_a_full, entry_b_bare):
    entries = (entry_a_full, entry_b_bare)
    weights, drawdown = _weights_and_drawdown(entries)
    stats = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    for value in (stats.portfolio_sharpe_ratio, stats.portfolio_sortino_ratio, stats.portfolio_calmar_ratio):
        assert value is None or isinstance(value, float)
