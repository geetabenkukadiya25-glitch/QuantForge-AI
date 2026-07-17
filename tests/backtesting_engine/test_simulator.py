"""`TradeSimulator`: determinism, trade production, and no-look-ahead behavior."""

from app.backtesting_engine.models import ExitReason
from app.backtesting_engine.simulator import TradeSimulator


def test_simulation_produces_trades(backtest_context) -> None:
    output = TradeSimulator().run(backtest_context)
    assert len(output.trades) > 0
    assert len(output.equity_curve.points) == len(backtest_context.data)


def test_simulation_is_deterministic(backtest_context) -> None:
    output1 = TradeSimulator().run(backtest_context)
    output2 = TradeSimulator().run(backtest_context)
    assert output1.trades == output2.trades
    assert output1.equity_curve == output2.equity_curve


def test_equity_curve_starts_near_initial_balance(backtest_context) -> None:
    output = TradeSimulator().run(backtest_context)
    first_equity = output.equity_curve.points[0].equity
    assert abs(first_equity - backtest_context.configuration.initial_balance) < backtest_context.configuration.initial_balance * 0.05


def test_no_look_ahead_bias(backtest_context) -> None:
    """Truncating the dataset must not change trades already resolved well before the cutoff.

    If a later candle's data were leaking into an earlier decision, this
    truncation would change those earlier trades -- it must not.
    """
    full_output = TradeSimulator().run(backtest_context)

    truncated_data = backtest_context.data.iloc[:100].reset_index(drop=True)
    from dataclasses import replace

    truncated_context = replace(backtest_context, data=truncated_data)
    truncated_output = TradeSimulator().run(truncated_context)

    safety_margin = 90  # stay well clear of the truncated run's forced end-of-data close

    def _resolved_before_margin(trades):
        return [
            t
            for t in trades
            if t.entry_index < safety_margin
            and t.exit_index is not None
            and t.exit_index < safety_margin
            and t.exit_reason != ExitReason.END_OF_DATA
        ]

    full_resolved = _resolved_before_margin(full_output.trades)
    truncated_resolved = _resolved_before_margin(truncated_output.trades)

    assert full_resolved == truncated_resolved
    assert len(full_resolved) > 0  # the assertion above would be vacuous otherwise
