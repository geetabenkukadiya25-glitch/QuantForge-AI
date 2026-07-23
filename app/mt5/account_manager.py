"""Read-only `MetaTrader5.account_info()` wrapper (Phase 19.0). Reporting
only -- nothing here submits an order, modifies a position, or acts on
the account in any way.
"""

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import AccountInfo, ConnectionState


def get_account_info(connection: ConnectionManager) -> AccountInfo:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read account info -- not connected.")
    mt5 = import_mt5()
    info = mt5.account_info()
    if info is None:
        raise MT5ConnectionError("account_info() returned None.")
    return AccountInfo(
        login=int(getattr(info, "login", 0)),
        server=str(getattr(info, "server", "")),
        currency=str(getattr(info, "currency", "")),
        balance=float(getattr(info, "balance", 0.0)),
        equity=float(getattr(info, "equity", 0.0)),
        margin=float(getattr(info, "margin", 0.0)),
        margin_free=float(getattr(info, "margin_free", 0.0)),
        leverage=int(getattr(info, "leverage", 0)),
        trade_allowed=bool(getattr(info, "trade_allowed", False)),
    )
