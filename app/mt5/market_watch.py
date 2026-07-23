"""Read-only live quote / market-depth snapshot (Phase 19.0). Wraps
`MetaTrader5.symbol_info_tick()` and `market_book_get()` -- reporting
only, no order book action taken.
"""

from dataclasses import dataclass

from app.mt5.connection_manager import ConnectionManager, import_mt5
from app.mt5.exceptions import MT5ConnectionError, MT5SymbolNotFoundError
from app.mt5.mt5_models import ConnectionState


@dataclass(frozen=True)
class QuoteSnapshot:
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    time: float  # unix seconds, as reported by the terminal


@dataclass(frozen=True)
class DepthLevel:
    price: float
    volume: float
    type_: str  # "buy" or "sell"


def get_quote(connection: ConnectionManager, symbol: str) -> QuoteSnapshot:
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read a quote -- not connected.")
    mt5 = import_mt5()
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise MT5SymbolNotFoundError(f"No tick data for symbol '{symbol}'.")
    return QuoteSnapshot(
        symbol=symbol,
        bid=float(getattr(tick, "bid", 0.0)),
        ask=float(getattr(tick, "ask", 0.0)),
        last=float(getattr(tick, "last", 0.0)),
        volume=int(getattr(tick, "volume", 0)),
        time=float(getattr(tick, "time", 0)),
    )


def get_market_depth(connection: ConnectionManager, symbol: str) -> list[DepthLevel]:
    """Best-effort market book snapshot. Not every symbol/broker exposes
    depth-of-market -- an empty list is a normal outcome, not an error."""
    if connection.state != ConnectionState.CONNECTED:
        raise MT5ConnectionError("Cannot read market depth -- not connected.")
    mt5 = import_mt5()
    if not mt5.market_book_add(symbol):
        return []
    try:
        book = mt5.market_book_get(symbol)
        if not book:
            return []
        return [
            DepthLevel(
                price=float(getattr(level, "price", 0.0)),
                volume=float(getattr(level, "volume", 0.0)),
                type_="buy" if int(getattr(level, "type", 0)) == 0 else "sell",
            )
            for level in book
        ]
    finally:
        mt5.market_book_release(symbol)
