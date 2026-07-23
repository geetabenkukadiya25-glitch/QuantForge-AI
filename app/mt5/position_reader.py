"""Read-only `MetaTrader5.positions_get()` wrapper (Phase 19.1). Reporting
only -- nothing here closes, modifies, or hedges a position; there is no
such function anywhere in `app.mt5`.
"""

from datetime import datetime

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import ConnectionState, PositionInfo


def _to_position_info(raw) -> PositionInfo:
    return PositionInfo(
        ticket=int(getattr(raw, "ticket", 0)),
        symbol=str(getattr(raw, "symbol", "")),
        type=int(getattr(raw, "type", 0)),
        volume=float(getattr(raw, "volume", 0.0)),
        price_open=float(getattr(raw, "price_open", 0.0)),
        sl=float(getattr(raw, "sl", 0.0)),
        tp=float(getattr(raw, "tp", 0.0)),
        price_current=float(getattr(raw, "price_current", 0.0)),
        profit=float(getattr(raw, "profit", 0.0)),
        swap=float(getattr(raw, "swap", 0.0)),
        time=datetime.fromtimestamp(int(getattr(raw, "time", 0))),
        magic=int(getattr(raw, "magic", 0)),
        comment=str(getattr(raw, "comment", "")),
    )


def get_positions(connection: ConnectionManager, symbol: str | None = None) -> list[PositionInfo]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read positions -- not connected.")
    mt5 = import_mt5()
    raw_positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    if raw_positions is None:
        return []
    return [_to_position_info(raw) for raw in raw_positions]
