"""Simulated order fills, pending-order triggering, and position lifecycle orchestration.

`ExecutionEngine` is the single place that turns a trading decision into a
`Trade` lifecycle event. It owns no broker connection, no MT5 handle, and
no network socket -- every fill price is computed locally from
`BacktestConfiguration`'s spread/slippage placeholders (see
`OrderSimulator`), and every position change comes from `PositionManager`.
"""

from dataclasses import dataclass

from app.backtesting_engine.models import BacktestConfiguration, ExecutionEvent, ExitReason, Trade, TradeDirection
from app.backtesting_engine.position import PositionManager


class OrderSimulator:
    """Computes deterministic fill prices under configured spread/slippage assumptions.

    Spread and slippage are modeled as a fixed adverse price offset,
    applied identically to every fill -- a simplified, framework-level
    execution assumption (see `BacktestConfiguration`), not a broker-grade
    order book simulation.
    """

    def fill_price(self, direction: TradeDirection, reference_price: float, configuration: BacktestConfiguration) -> float:
        adverse_offset = configuration.spread_points + configuration.slippage_points
        if direction == TradeDirection.BUY:
            return reference_price + adverse_offset
        return reference_price - adverse_offset


@dataclass
class PendingOrder:
    """A queued, not-yet-filled order awaiting its trigger price."""

    order_id: str
    direction: TradeDirection
    trigger_price: float
    volume: float
    stop_loss: float | None
    take_profit: float | None
    created_index: int


class ExecutionEngine:
    """Coordinates pending-order triggering, fills, and position lifecycle for one run.

    `latency_bars` on `BacktestConfiguration` is honored only as a
    framework placeholder here: pending orders always trigger on the
    first candle whose high/low crosses the trigger price, they are never
    delayed further -- true multi-bar latency simulation is left for a
    future phase (see `PROJECT_IDEAS.md`).
    """

    def __init__(
        self,
        configuration: BacktestConfiguration,
        position_manager: PositionManager | None = None,
        order_simulator: OrderSimulator | None = None,
    ) -> None:
        self._configuration = configuration
        self._positions = position_manager or PositionManager(configuration)
        self._orders = order_simulator or OrderSimulator()
        self._pending: dict[str, PendingOrder] = {}
        self._next_order_id = 1

    @property
    def positions(self) -> PositionManager:
        return self._positions

    def submit_market_order(
        self,
        index: int,
        dt: str,
        direction: TradeDirection,
        reference_price: float,
        volume: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> tuple[str | None, ExecutionEvent]:
        """Fill a market order immediately, or reject it if at `max_open_positions`."""
        if not self._positions.can_open():
            return None, ExecutionEvent(
                index=index, datetime=dt, event_type="ORDER_REJECTED", message="Max open positions reached."
            )
        fill_price = self._orders.fill_price(direction, reference_price, self._configuration)
        trade_id = self._positions.open_position(index, dt, direction, fill_price, volume, stop_loss, take_profit)
        event = ExecutionEvent(
            index=index,
            datetime=dt,
            event_type="POSITION_OPEN",
            message=f"{direction.value} {volume} @ {fill_price:.5f} (trade {trade_id})",
        )
        return trade_id, event

    def submit_pending_order(
        self,
        index: int,
        direction: TradeDirection,
        trigger_price: float,
        volume: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> str:
        """Queue a pending order; it fills on a future candle whose range crosses `trigger_price`."""
        order_id = f"P{self._next_order_id:06d}"
        self._next_order_id += 1
        self._pending[order_id] = PendingOrder(order_id, direction, trigger_price, volume, stop_loss, take_profit, index)
        return order_id

    def process_candle(
        self, index: int, dt: str, high: float, low: float, close: float
    ) -> tuple[list[ExecutionEvent], list[Trade]]:
        """Advance the simulation by one candle: trigger pending orders, then evaluate exits."""
        events: list[ExecutionEvent] = []

        for order_id in list(self._pending):
            order = self._pending[order_id]
            if low <= order.trigger_price <= high:
                del self._pending[order_id]
                events.append(
                    ExecutionEvent(index=index, datetime=dt, event_type="ORDER_TRIGGERED", message=f"Pending order {order_id} triggered.")
                )
                trade_id, open_event = self.submit_market_order(
                    index, dt, order.direction, order.trigger_price, order.volume, order.stop_loss, order.take_profit
                )
                events.append(open_event)

        closed_trades = self._positions.check_candle(index, dt, high, low, close)
        for trade in closed_trades:
            events.append(
                ExecutionEvent(
                    index=index,
                    datetime=dt,
                    event_type="POSITION_CLOSE",
                    message=f"{trade.exit_reason.value} trade {trade.trade_id} @ {trade.exit_price:.5f} (net {trade.net_profit:.2f})",
                )
            )
            events.append(ExecutionEvent(index=index, datetime=dt, event_type="TRADE_COMPLETE", message=f"Trade {trade.trade_id} complete."))

        return events, closed_trades

    def close_all(self, index: int, dt: str, price: float, reason: ExitReason = ExitReason.END_OF_DATA) -> tuple[list[ExecutionEvent], list[Trade]]:
        """Force-close every open position (e.g. at the end of historical data)."""
        closed_trades = self._positions.close_all(index, dt, price, reason)
        events = [
            ExecutionEvent(
                index=index,
                datetime=dt,
                event_type="POSITION_CLOSE",
                message=f"{trade.exit_reason.value} trade {trade.trade_id} @ {trade.exit_price:.5f} (net {trade.net_profit:.2f})",
            )
            for trade in closed_trades
        ]
        return events, closed_trades
