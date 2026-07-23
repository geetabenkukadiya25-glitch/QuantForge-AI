"""Read-only tick-history wrapper (Phase 19.0). Wraps
`MetaTrader5.copy_ticks_from`/`copy_ticks_range`.
"""

from datetime import datetime

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import ConnectionState, Tick

_COPY_TICKS_ALL = -1


def _to_tick(raw) -> Tick:
    return Tick(
        time=datetime.fromtimestamp(int(raw["time"])),
        bid=float(raw["bid"]),
        ask=float(raw["ask"]),
        last=float(raw["last"]),
        volume=int(raw["volume"]),
        flags=int(raw["flags"]),
    )


def copy_ticks_from(connection: ConnectionManager, symbol: str, from_date: datetime, count: int) -> list[Tick]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read ticks -- not connected.")
    mt5 = import_mt5()
    ticks = mt5.copy_ticks_from(symbol, from_date, count, _COPY_TICKS_ALL)
    if ticks is None:
        return []
    return [_to_tick(t) for t in ticks]


def copy_ticks_range(connection: ConnectionManager, symbol: str, date_from: datetime, date_to: datetime) -> list[Tick]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read ticks -- not connected.")
    mt5 = import_mt5()
    ticks = mt5.copy_ticks_range(symbol, date_from, date_to, _COPY_TICKS_ALL)
    if ticks is None:
        return []
    return [_to_tick(t) for t in ticks]
