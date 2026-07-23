"""Read-only OHLCV history wrapper (Phase 19.0). Wraps
`MetaTrader5.copy_rates_from`/`copy_rates_range` -- never writes to, or
modifies, any dataset; this is a live/terminal-side read only. If a
future phase wants MT5 history inside Dataset Manager, that would be a
Dataset Manager import feature added there, not logic duplicated here.
"""

from datetime import datetime

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import Bar, ConnectionState
from app.mt5.timeframe_manager import to_mt5_timeframe


def _to_bar(raw) -> Bar:
    return Bar(
        time=datetime.fromtimestamp(int(raw["time"])),
        open=float(raw["open"]),
        high=float(raw["high"]),
        low=float(raw["low"]),
        close=float(raw["close"]),
        tick_volume=int(raw["tick_volume"]),
        spread=int(raw["spread"]),
        real_volume=int(raw["real_volume"]),
    )


def copy_rates_from(connection: ConnectionManager, symbol: str, timeframe: str, from_date: datetime, count: int) -> list[Bar]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read history -- not connected.")
    mt5 = import_mt5()
    rates = mt5.copy_rates_from(symbol, to_mt5_timeframe(timeframe), from_date, count)
    if rates is None:
        return []
    return [_to_bar(r) for r in rates]


def copy_rates_range(connection: ConnectionManager, symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> list[Bar]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read history -- not connected.")
    mt5 = import_mt5()
    rates = mt5.copy_rates_range(symbol, to_mt5_timeframe(timeframe), date_from, date_to)
    if rates is None:
        return []
    return [_to_bar(r) for r in rates]
