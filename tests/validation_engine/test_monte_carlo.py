"""`MonteCarloEngine`: resampling an already-produced trade list, never simulating new trades."""

from app.backtesting_engine.models import ExitReason, Trade, TradeDirection, TradeStatus
from app.validation_engine.models import MonteCarloConfiguration, MonteCarloMethod
from app.validation_engine.monte_carlo import MonteCarloEngine


def _trade(net_profit: float) -> Trade:
    return Trade(
        trade_id=f"T-{net_profit}", direction=TradeDirection.BUY, entry_index=0, entry_datetime="t0", entry_price=100.0,
        volume=1.0, exit_index=1, exit_datetime="t1", exit_price=100.0 + net_profit, status=TradeStatus.CLOSED,
        exit_reason=ExitReason.SIGNAL, gross_profit=net_profit, commission=0.0, swap=0.0,
    )


def _trades() -> tuple[Trade, ...]:
    return tuple(_trade(v) for v in [10.0, -5.0, 20.0, -8.0, 15.0, -3.0, 7.0, -12.0])


def _config(method: MonteCarloMethod, **overrides) -> MonteCarloConfiguration:
    base = {"method": method, "iterations": 50, "random_seed": 7}
    base.update(overrides)
    return MonteCarloConfiguration(**base)


def test_produces_requested_iteration_count() -> None:
    result = MonteCarloEngine().run(_trades(), 10_000.0, _config(MonteCarloMethod.TRADE_SHUFFLE))
    assert result.iterations_run == 50
    assert len(result.distribution) == 50


def test_trade_shuffle_preserves_total_net_profit_every_iteration() -> None:
    trades = _trades()
    total = sum(t.net_profit for t in trades)
    result = MonteCarloEngine().run(trades, 10_000.0, _config(MonteCarloMethod.TRADE_SHUFFLE))
    for point in result.distribution:
        assert abs(point.net_profit - total) < 1e-9


def test_bootstrap_varies_net_profit_across_iterations() -> None:
    result = MonteCarloEngine().run(_trades(), 10_000.0, _config(MonteCarloMethod.BOOTSTRAP, iterations=100))
    net_profits = {round(p.net_profit, 6) for p in result.distribution}
    assert len(net_profits) > 1  # sampling with replacement should produce varied outcomes


def test_deterministic_given_same_seed() -> None:
    trades = _trades()
    config = _config(MonteCarloMethod.BOOTSTRAP, iterations=30, random_seed=99)
    result1 = MonteCarloEngine().run(trades, 10_000.0, config)
    result2 = MonteCarloEngine().run(trades, 10_000.0, config)
    assert result1 == result2


def test_different_seed_changes_distribution() -> None:
    trades = _trades()
    result1 = MonteCarloEngine().run(trades, 10_000.0, _config(MonteCarloMethod.BOOTSTRAP, iterations=30, random_seed=1))
    result2 = MonteCarloEngine().run(trades, 10_000.0, _config(MonteCarloMethod.BOOTSTRAP, iterations=30, random_seed=2))
    assert result1.distribution != result2.distribution


def test_probability_of_profit_is_fraction_of_positive_outcomes() -> None:
    all_winners = tuple(_trade(v) for v in [5.0, 10.0, 3.0])
    result = MonteCarloEngine().run(all_winners, 10_000.0, _config(MonteCarloMethod.TRADE_SHUFFLE, iterations=20))
    assert result.probability_of_profit == 1.0


def test_confidence_interval_bounds_are_within_distribution() -> None:
    result = MonteCarloEngine().run(_trades(), 10_000.0, _config(MonteCarloMethod.BOOTSTRAP, iterations=200))
    net_profits = [p.net_profit for p in result.distribution]
    assert min(net_profits) <= result.confidence_interval_low <= max(net_profits)
    assert min(net_profits) <= result.confidence_interval_high <= max(net_profits)
    assert result.confidence_interval_low <= result.confidence_interval_high


def test_empty_trades_produces_flat_iterations() -> None:
    # No closed trades means resampling has nothing to draw from -- every
    # iteration is a no-op, so equity stays flat rather than the run being skipped.
    result = MonteCarloEngine().run((), 10_000.0, _config(MonteCarloMethod.BOOTSTRAP, iterations=10))
    assert result.iterations_run == 10
    assert all(p.net_profit == 0.0 for p in result.distribution)
    assert result.probability_of_profit == 0.0


def test_return_shuffle_produces_finite_results() -> None:
    # RETURN_SHUFFLE treats each trade's profit as a fractional return of
    # the initial balance, applied multiplicatively -- distinct from the
    # additive P&L path TRADE_SHUFFLE/BOOTSTRAP use.
    result = MonteCarloEngine().run(_trades(), 10_000.0, _config(MonteCarloMethod.RETURN_SHUFFLE, iterations=20))
    assert result.iterations_run == 20
    assert all(p.final_equity == p.final_equity for p in result.distribution)  # not NaN
