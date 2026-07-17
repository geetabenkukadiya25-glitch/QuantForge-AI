"""Tracks open simulated positions and closes them into immutable `Trade`s.

`PositionManager` owns the only mutable state in the simulation: the set
of currently-open positions for one run. Every candle it is asked to
evaluate stop loss / take profit / break-even against only that candle's
own high/low/close -- it never looks at data beyond the index it is
given, which is what guarantees the simulation has no look-ahead bias.
"""

from dataclasses import dataclass, field

from app.backtesting_engine.models import BacktestConfiguration, ExitReason, Trade, TradeDirection, TradeStatus


@dataclass
class _OpenPosition:
    """Mutable working state for one not-yet-closed position."""

    trade_id: str
    direction: TradeDirection
    entry_index: int
    entry_datetime: str
    entry_price: float
    volume: float
    stop_loss: float | None = None
    take_profit: float | None = None
    break_even_triggered: bool = False


class PositionManager:
    """Opens, updates, and closes simulated positions for one backtest run."""

    def __init__(self, configuration: BacktestConfiguration) -> None:
        self._configuration = configuration
        self._open: dict[str, _OpenPosition] = {}
        self._next_id = 1

    @property
    def open_count(self) -> int:
        return len(self._open)

    def can_open(self) -> bool:
        return self.open_count < self._configuration.max_open_positions

    def open_position(
        self,
        index: int,
        dt: str,
        direction: TradeDirection,
        fill_price: float,
        volume: float,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> str:
        """Open a new position at an already-computed `fill_price`. Returns the new trade id."""
        trade_id = f"T{self._next_id:06d}"
        self._next_id += 1
        self._open[trade_id] = _OpenPosition(
            trade_id=trade_id,
            direction=direction,
            entry_index=index,
            entry_datetime=dt,
            entry_price=fill_price,
            volume=volume,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        return trade_id

    def floating_pnl(self, current_price: float) -> float:
        """Unrealized profit across every open position, at `current_price`."""
        total = 0.0
        for pos in self._open.values():
            sign = 1 if pos.direction == TradeDirection.BUY else -1
            total += (current_price - pos.entry_price) * sign * pos.volume * self._configuration.point_value
        return total

    def check_candle(self, index: int, dt: str, high: float, low: float, close: float) -> list[Trade]:
        """Evaluate break-even, stop loss, and take profit for every open position at this candle.

        Trailing stop and partial close are framework placeholders only
        (per the Phase 9 spec) -- `enable_trailing_stop`/
        `enable_partial_close` are accepted on `BacktestConfiguration` but
        do not change position sizing or stop distance here.
        """
        closed: list[Trade] = []
        for trade_id in list(self._open):
            pos = self._open[trade_id]
            self._maybe_apply_break_even(pos, high, low)
            exit_price, reason = self._check_exit(pos, high, low)
            if exit_price is not None:
                closed.append(self._close(trade_id, index, dt, exit_price, reason))
        return closed

    def _maybe_apply_break_even(self, pos: _OpenPosition, high: float, low: float) -> None:
        """Move stop loss to entry once price has moved favorably by the initial risk distance."""
        if pos.break_even_triggered or pos.stop_loss is None:
            return
        risk = abs(pos.entry_price - pos.stop_loss)
        if risk <= 0:
            return
        if pos.direction == TradeDirection.BUY:
            target = pos.entry_price + risk
            triggered = high >= target
        else:
            target = pos.entry_price - risk
            triggered = low <= target
        if triggered:
            pos.stop_loss = pos.entry_price
            pos.break_even_triggered = True

    @staticmethod
    def _check_exit(pos: _OpenPosition, high: float, low: float) -> tuple[float | None, ExitReason | None]:
        """Return (exit_price, reason) if `pos` should close this candle, else (None, None).

        If both stop loss and take profit are crossed within the same
        candle, stop loss takes priority -- a deterministic, conservative
        tie-break (the same candle can't reveal which was hit first).
        """
        if pos.direction == TradeDirection.BUY:
            if pos.stop_loss is not None and low <= pos.stop_loss:
                reason = ExitReason.BREAK_EVEN if pos.break_even_triggered and pos.stop_loss == pos.entry_price else ExitReason.STOP_LOSS
                return pos.stop_loss, reason
            if pos.take_profit is not None and high >= pos.take_profit:
                return pos.take_profit, ExitReason.TAKE_PROFIT
        else:
            if pos.stop_loss is not None and high >= pos.stop_loss:
                reason = ExitReason.BREAK_EVEN if pos.break_even_triggered and pos.stop_loss == pos.entry_price else ExitReason.STOP_LOSS
                return pos.stop_loss, reason
            if pos.take_profit is not None and low <= pos.take_profit:
                return pos.take_profit, ExitReason.TAKE_PROFIT
        return None, None

    def close_all(self, index: int, dt: str, price: float, reason: ExitReason) -> list[Trade]:
        """Force-close every open position at `price` (e.g. end of historical data)."""
        return [self._close(trade_id, index, dt, price, reason) for trade_id in list(self._open)]

    def _close(self, trade_id: str, index: int, dt: str, exit_price: float, reason: ExitReason) -> Trade:
        pos = self._open.pop(trade_id)
        sign = 1 if pos.direction == TradeDirection.BUY else -1
        gross_profit = (exit_price - pos.entry_price) * sign * pos.volume * self._configuration.point_value
        commission = self._configuration.commission_per_lot * pos.volume
        swap = self._swap_charge(pos, dt)
        return Trade(
            trade_id=pos.trade_id,
            direction=pos.direction,
            entry_index=pos.entry_index,
            entry_datetime=pos.entry_datetime,
            entry_price=pos.entry_price,
            volume=pos.volume,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            exit_index=index,
            exit_datetime=dt,
            exit_price=exit_price,
            status=TradeStatus.CLOSED,
            exit_reason=reason,
            gross_profit=gross_profit,
            commission=commission,
            swap=swap,
        )

    def _swap_charge(self, pos: _OpenPosition, exit_datetime: str) -> float:
        try:
            days_held = max(0, (_parse_date(exit_datetime) - _parse_date(pos.entry_datetime)).days)
        except (ValueError, TypeError):
            days_held = 0
        rate = self._configuration.swap_long_per_day if pos.direction == TradeDirection.BUY else self._configuration.swap_short_per_day
        return rate * pos.volume * days_held


def _parse_date(value: str):
    import pandas as pd

    return pd.Timestamp(value)
