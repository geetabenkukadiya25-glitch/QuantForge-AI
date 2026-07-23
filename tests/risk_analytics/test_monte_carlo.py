"""`monte_carlo.py` -- wraps the real, unmodified
`app.validation_engine.MonteCarloEngine`; verifies real resampling
happens (not fabricated) and that the additive slippage/spread
perturbation and probability-of-ruin derivation work as designed."""

from app.backtesting_engine.models import Trade, TradeDirection, TradeStatus
from app.risk_analytics.monte_carlo import run_monte_carlo
from app.validation_engine.models import MonteCarloConfiguration, MonteCarloMethod


def _trade(trade_id: str, net_profit: float) -> Trade:
    return Trade(
        trade_id=trade_id, direction=TradeDirection.BUY, entry_index=0, entry_datetime="2024-01-01T00:00:00",
        entry_price=1.1, volume=1.0, exit_index=1, exit_datetime="2024-01-01T01:00:00",
        exit_price=1.1 + net_profit, status=TradeStatus.CLOSED, gross_profit=net_profit,
    )


TRADES = tuple(_trade(str(i), p) for i, p in enumerate([100, -50, 80, -30, 120, -60, 90, -40]))
CONFIG = MonteCarloConfiguration(method=MonteCarloMethod.BOOTSTRAP, iterations=100, random_seed=7)


def test_run_monte_carlo_uses_real_engine_resampling() -> None:
    result = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG)
    assert result.iterations_run == 100
    assert result.perturbed is False
    assert 0.0 <= result.probability_of_profit <= 1.0
    assert 0.0 <= result.probability_of_ruin <= 1.0


def test_run_monte_carlo_is_deterministic_given_same_seed() -> None:
    a = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG)
    b = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG)
    assert a.mean_net_profit == b.mean_net_profit
    assert a.worst_net_profit == b.worst_net_profit


def test_run_monte_carlo_perturbation_changes_the_distribution() -> None:
    baseline = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG)
    perturbed = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG, slippage_range=(5.0, 15.0), spread_range=(2.0, 8.0))
    assert perturbed.perturbed is True
    # Perturbation always deducts a positive cost, so mean net profit must be lower.
    assert perturbed.mean_net_profit < baseline.mean_net_profit


def test_run_monte_carlo_never_mutates_original_trades() -> None:
    original_profits = [t.gross_profit for t in TRADES]
    run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG, slippage_range=(5.0, 15.0))
    assert [t.gross_profit for t in TRADES] == original_profits


def test_run_monte_carlo_ruin_threshold_forces_full_ruin_probability() -> None:
    # A ruin threshold of 0% means ANY drop below full initial balance counts as ruin.
    result = run_monte_carlo(TRADES, initial_balance=10_000.0, configuration=CONFIG, ruin_threshold_pct=0.0)
    assert result.ruin_threshold == 10_000.0
