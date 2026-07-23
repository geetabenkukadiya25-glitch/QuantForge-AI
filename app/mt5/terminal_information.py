"""Read-only `MetaTrader5.terminal_info()` wrapper (Phase 19.0)."""

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import TerminalInfo


def get_terminal_info(connection: ConnectionManager) -> TerminalInfo:
    from app.mt5.mt5_models import ConnectionState

    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read terminal info -- not connected.")
    mt5 = import_mt5()
    info = mt5.terminal_info()
    if info is None:
        raise MT5ConnectionError("terminal_info() returned None.")
    return TerminalInfo(
        community_account=bool(getattr(info, "community_account", False)),
        connected=bool(getattr(info, "connected", False)),
        trade_allowed=bool(getattr(info, "trade_allowed", False)),
        trade_expert=bool(getattr(info, "trade_expert", False)),
        build=int(getattr(info, "build", 0)),
        name=str(getattr(info, "name", "")),
        company=str(getattr(info, "company", "")),
        path=str(getattr(info, "path", "")),
        data_path=str(getattr(info, "data_path", "")),
    )
