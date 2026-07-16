"""Shared column and timeframe conventions for the historical data engine.

Every `data_engine` component reads/writes DataFrames using these
constants so the standard schema stays defined in exactly one place.
"""

import re

# Standard output schema, in order.
DATETIME_COL = "Datetime"
OHLC_COLS = ["Open", "High", "Low", "Close"]
VOLUME_COL = "Volume"
SPREAD_COL = "Spread"

STANDARD_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL, SPREAD_COL]

# Maps a normalized (lowercase, alnum-only) source header to its canonical
# standard-schema name. Covers both plain CSV exports ("Tick Volume") and
# raw MetaTrader 5 terminal exports ("<TICKVOL>").
_HEADER_ALIASES: dict[str, str] = {
    "date": "Date",
    "time": "Time",
    "datetime": "Datetime",
    "open": "Open",
    "high": "High",
    "low": "Low",
    "close": "Close",
    "tickvolume": "TickVolume",
    "tickvol": "TickVolume",
    "volume": "Volume",
    "vol": "Volume",
    "spread": "Spread",
}

# Standard timeframe labels mapped to pandas resample offset aliases.
TIMEFRAME_TO_PANDAS_FREQ: dict[str, str] = {
    "M1": "1min",
    "M5": "5min",
    "M15": "15min",
    "M30": "30min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
    "W1": "1W",
    "MN1": "1MS",
}


def normalize_header(raw: str) -> str:
    """Strip MT5-style angle brackets/whitespace and lowercase to alnum-only."""
    return re.sub(r"[^a-z0-9]", "", raw.strip().strip("<>").lower())


def resolve_header_aliases(columns: list[str]) -> dict[str, str]:
    """Map each raw column name to its canonical name, where recognized."""
    resolved: dict[str, str] = {}
    for raw in columns:
        canonical = _HEADER_ALIASES.get(normalize_header(raw))
        if canonical is not None:
            resolved[raw] = canonical
    return resolved
