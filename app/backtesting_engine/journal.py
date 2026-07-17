"""A queryable view over a completed backtest's trades.

`TradeJournal` wraps the immutable `Trade` tuple already carried on a
`BacktestResult` -- it never mutates trades or re-runs the simulation; it
only presents them (e.g. as a `pandas.DataFrame` for the Streamlit
Trade List / Trade Journal reports).
"""

import pandas as pd

from app.backtesting_engine.models import ExitReason, Trade, TradeDirection


class TradeJournal:
    """Read-only, queryable wrapper around a run's closed (and open) trades."""

    def __init__(self, trades: tuple[Trade, ...] | list[Trade]) -> None:
        self._trades = tuple(trades)

    @property
    def trades(self) -> tuple[Trade, ...]:
        return self._trades

    def filter_by_direction(self, direction: TradeDirection) -> tuple[Trade, ...]:
        return tuple(t for t in self._trades if t.direction == direction)

    def filter_by_exit_reason(self, reason: ExitReason) -> tuple[Trade, ...]:
        return tuple(t for t in self._trades if t.exit_reason == reason)

    def winning_trades(self) -> tuple[Trade, ...]:
        return tuple(t for t in self._trades if t.net_profit > 0)

    def losing_trades(self) -> tuple[Trade, ...]:
        return tuple(t for t in self._trades if t.net_profit < 0)

    def to_dataframe(self) -> pd.DataFrame:
        """Return the journal as a flat `pandas.DataFrame`, one row per trade."""
        if not self._trades:
            return pd.DataFrame(
                columns=[
                    "trade_id", "direction", "entry_datetime", "entry_price", "exit_datetime",
                    "exit_price", "volume", "exit_reason", "gross_profit", "commission", "swap", "net_profit",
                ]
            )
        return pd.DataFrame(
            [
                {
                    "trade_id": t.trade_id,
                    "direction": t.direction.value,
                    "entry_datetime": t.entry_datetime,
                    "entry_price": t.entry_price,
                    "exit_datetime": t.exit_datetime,
                    "exit_price": t.exit_price,
                    "volume": t.volume,
                    "exit_reason": t.exit_reason.value if t.exit_reason else None,
                    "gross_profit": t.gross_profit,
                    "commission": t.commission,
                    "swap": t.swap,
                    "net_profit": t.net_profit,
                }
                for t in self._trades
            ]
        )

    def summary(self) -> dict:
        """A small, dict-shaped summary (counts and totals) -- not a replacement for `PerformanceStatistics`."""
        return {
            "total_trades": len(self._trades),
            "winning_trades": len(self.winning_trades()),
            "losing_trades": len(self.losing_trades()),
            "net_profit": sum(t.net_profit for t in self._trades),
        }
