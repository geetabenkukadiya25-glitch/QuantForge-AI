"""Read-only `MetaTrader5.symbols_get()`/`symbol_info()` wrappers
(Phase 19.0)."""

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError, MT5SymbolNotFoundError
from app.mt5.mt5_models import ConnectionState, SymbolInfo


def _to_symbol_info(raw) -> SymbolInfo:
    return SymbolInfo(
        name=str(getattr(raw, "name", "")),
        description=str(getattr(raw, "description", "")),
        path=str(getattr(raw, "path", "")),
        digits=int(getattr(raw, "digits", 0)),
        point=float(getattr(raw, "point", 0.0)),
        visible=bool(getattr(raw, "visible", False)),
        spread=int(getattr(raw, "spread", 0)),
    )


def list_symbols(connection: ConnectionManager, group: str | None = None) -> list[SymbolInfo]:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot list symbols -- not connected.")
    mt5 = import_mt5()
    raw_symbols = mt5.symbols_get(group) if group else mt5.symbols_get()
    if raw_symbols is None:
        return []
    return [_to_symbol_info(raw) for raw in raw_symbols]


def get_symbol_info(connection: ConnectionManager, symbol: str) -> SymbolInfo:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read symbol info -- not connected.")
    mt5 = import_mt5()
    raw = mt5.symbol_info(symbol)
    if raw is None:
        raise MT5SymbolNotFoundError(f"Symbol '{symbol}' is not available on the connected terminal.")
    return _to_symbol_info(raw)
