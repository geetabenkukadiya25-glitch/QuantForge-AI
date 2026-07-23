"""Read-only `MetaTrader5.orders_get()` wrapper (Phase 19.1) -- lists
PENDING orders. Reporting only -- nothing here places, modifies, or
cancels an order; there is no such function anywhere in `app.mt5`.
"""

from datetime import datetime

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import ConnectionState, OrderInfo


def _to_order_info(raw) -> OrderInfo:
    return OrderInfo(
        ticket=int(getattr(raw, "ticket", 0)),
        symbol=str(getattr(raw, "symbol", "")),
        type=int(getattr(raw, "type", 0)),
        state=int(getattr(raw, "state", 0)),
        volume_current=float(getattr(raw, "volume_current", 0.0)),
        price_open=float(getattr(raw, "price_open", 0.0)),
        sl=float(getattr(raw, "sl", 0.0)),
        tp=float(getattr(raw, "tp", 0.0)),
        price_current=float(getattr(raw, "price_current", 0.0)),
        time_setup=datetime.fromtimestamp(int(getattr(raw, "time_setup", 0))),
        magic=int(getattr(raw, "magic", 0)),
        comment=str(getattr(raw, "comment", "")),
    )


def get_orders(connection: ConnectionManager, symbol: str | None = None) -> list[OrderInfo]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read orders -- not connected.")
    mt5 = import_mt5()
    raw_orders = mt5.orders_get(symbol=symbol) if symbol else mt5.orders_get()
    if raw_orders is None:
        return []
    return [_to_order_info(raw) for raw in raw_orders]
