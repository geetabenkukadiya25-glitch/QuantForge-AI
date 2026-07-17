"""`PositionManager`: open, break-even, stop loss, take profit, close-all."""

from app.backtesting_engine.models import BacktestConfiguration, ExitReason, TradeDirection
from app.backtesting_engine.position import PositionManager


def _config(**overrides) -> BacktestConfiguration:
    base = {"symbol": "EURUSD", "timeframe": "H1", "max_open_positions": 1}
    base.update(overrides)
    return BacktestConfiguration(**base)


def test_open_and_can_open_respects_max_positions() -> None:
    manager = PositionManager(_config(max_open_positions=1))
    assert manager.can_open() is True
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    assert manager.can_open() is False
    assert manager.open_count == 1


def test_take_profit_closes_buy_position() -> None:
    manager = PositionManager(_config())
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0, stop_loss=None, take_profit=110.0)
    closed = manager.check_candle(1, "t1", high=111.0, low=99.0, close=110.5)
    assert len(closed) == 1
    assert closed[0].exit_reason == ExitReason.TAKE_PROFIT
    assert closed[0].exit_price == 110.0
    assert manager.open_count == 0


def test_stop_loss_closes_sell_position() -> None:
    manager = PositionManager(_config())
    manager.open_position(0, "t0", TradeDirection.SELL, 100.0, 1.0, stop_loss=105.0, take_profit=90.0)
    closed = manager.check_candle(1, "t1", high=106.0, low=99.0, close=105.5)
    assert len(closed) == 1
    assert closed[0].exit_reason == ExitReason.STOP_LOSS
    assert closed[0].exit_price == 105.0


def test_stop_loss_takes_priority_when_both_hit_same_candle() -> None:
    # stop_loss is deliberately far (risk=10) so this candle's high (106)
    # doesn't also cross the break-even trigger (entry + risk = 110),
    # isolating the raw stop-loss-vs-take-profit tie-break being tested.
    manager = PositionManager(_config())
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0, stop_loss=90.0, take_profit=105.0)
    closed = manager.check_candle(1, "t1", high=106.0, low=89.0, close=100.0)
    assert closed[0].exit_reason == ExitReason.STOP_LOSS


def test_break_even_triggers_and_survives_when_low_stays_above_entry() -> None:
    manager = PositionManager(_config())
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0, stop_loss=95.0, take_profit=None)
    # Risk = 5; price must reach 105 to trigger break-even. Low stays above
    # the new (entry-level) stop, so the position survives this candle.
    closed = manager.check_candle(1, "t1", high=106.0, low=101.0, close=105.5)
    assert closed == []
    assert manager.open_count == 1


def test_break_even_can_close_the_position_within_the_same_candle() -> None:
    manager = PositionManager(_config())
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0, stop_loss=95.0, take_profit=None)
    # Same candle spans from a break-even-triggering high down to a low at
    # the entry price -- deterministically closes at break-even.
    closed = manager.check_candle(1, "t1", high=106.0, low=99.0, close=105.5)
    assert len(closed) == 1
    assert closed[0].exit_reason == ExitReason.BREAK_EVEN
    assert closed[0].exit_price == 100.0


def test_close_all_force_closes_every_open_position() -> None:
    manager = PositionManager(_config(max_open_positions=5))
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    manager.open_position(0, "t0", TradeDirection.SELL, 100.0, 1.0)
    closed = manager.close_all(5, "t5", price=101.0, reason=ExitReason.END_OF_DATA)
    assert len(closed) == 2
    assert all(t.exit_reason == ExitReason.END_OF_DATA for t in closed)
    assert manager.open_count == 0


def test_floating_pnl_reflects_direction() -> None:
    manager = PositionManager(_config(max_open_positions=5, point_value=2.0))
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    assert manager.floating_pnl(101.0) == 2.0
    manager.open_position(0, "t0", TradeDirection.SELL, 100.0, 1.0)
    assert manager.floating_pnl(101.0) == 2.0 + (-2.0)


def test_close_applies_commission() -> None:
    manager = PositionManager(_config(commission_per_lot=1.5))
    manager.open_position(0, "t0", TradeDirection.BUY, 100.0, 2.0)
    closed = manager.close_all(1, "t1", price=101.0, reason=ExitReason.MANUAL)
    assert closed[0].commission == 3.0
