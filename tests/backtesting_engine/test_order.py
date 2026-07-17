"""`OrderSimulator` fill prices and `ExecutionEngine` order/position lifecycle."""

from app.backtesting_engine.models import BacktestConfiguration, ExitReason, TradeDirection
from app.backtesting_engine.order import ExecutionEngine, OrderSimulator


def _config(**overrides) -> BacktestConfiguration:
    base = {"symbol": "EURUSD", "timeframe": "H1", "spread_points": 0.5, "slippage_points": 0.2}
    base.update(overrides)
    return BacktestConfiguration(**base)


def test_order_simulator_applies_adverse_offset_by_direction() -> None:
    sim = OrderSimulator()
    config = _config()
    assert sim.fill_price(TradeDirection.BUY, 100.0, config) == 100.7
    assert sim.fill_price(TradeDirection.SELL, 100.0, config) == 99.3


def test_market_order_opens_a_position() -> None:
    engine = ExecutionEngine(_config(spread_points=0.0, slippage_points=0.0))
    trade_id, event = engine.submit_market_order(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    assert trade_id is not None
    assert event.event_type == "POSITION_OPEN"
    assert engine.positions.open_count == 1


def test_market_order_rejected_at_max_positions() -> None:
    engine = ExecutionEngine(_config(max_open_positions=1, spread_points=0.0, slippage_points=0.0))
    engine.submit_market_order(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    trade_id, event = engine.submit_market_order(1, "t1", TradeDirection.BUY, 101.0, 1.0)
    assert trade_id is None
    assert event.event_type == "ORDER_REJECTED"


def test_pending_order_triggers_when_range_crosses_price() -> None:
    engine = ExecutionEngine(_config(spread_points=0.0, slippage_points=0.0))
    engine.submit_pending_order(0, TradeDirection.BUY, trigger_price=105.0, volume=1.0)
    events, closed = engine.process_candle(1, "t1", high=106.0, low=104.0, close=105.5)
    event_types = [e.event_type for e in events]
    assert "ORDER_TRIGGERED" in event_types
    assert "POSITION_OPEN" in event_types
    assert engine.positions.open_count == 1


def test_pending_order_does_not_trigger_outside_range() -> None:
    engine = ExecutionEngine(_config())
    engine.submit_pending_order(0, TradeDirection.BUY, trigger_price=200.0, volume=1.0)
    events, _ = engine.process_candle(1, "t1", high=106.0, low=104.0, close=105.5)
    assert events == []
    assert engine.positions.open_count == 0


def test_process_candle_reports_position_close_and_trade_complete() -> None:
    engine = ExecutionEngine(_config(spread_points=0.0, slippage_points=0.0))
    engine.submit_market_order(0, "t0", TradeDirection.BUY, 100.0, 1.0, stop_loss=None, take_profit=101.0)
    events, closed = engine.process_candle(1, "t1", high=102.0, low=99.0, close=101.5)
    assert len(closed) == 1
    event_types = [e.event_type for e in events]
    assert "POSITION_CLOSE" in event_types
    assert "TRADE_COMPLETE" in event_types


def test_close_all_uses_end_of_data_reason_by_default() -> None:
    engine = ExecutionEngine(_config(max_open_positions=5, spread_points=0.0, slippage_points=0.0))
    engine.submit_market_order(0, "t0", TradeDirection.BUY, 100.0, 1.0)
    events, closed = engine.close_all(10, "t10", price=105.0)
    assert closed[0].exit_reason == ExitReason.END_OF_DATA
