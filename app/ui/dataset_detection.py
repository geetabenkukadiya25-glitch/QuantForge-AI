"""Presentation-layer detection of a historical dataset's Symbol and Timeframe.

Pure, UI-only heuristics -- no engine, validator, or business logic is
touched or modified. Detection follows a fixed priority chain, per
source:

Symbol:      dataset metadata -> uploaded filename -> DataFrame attributes -> "Unknown"
Timeframe:   dataset metadata -> uploaded filename -> candle spacing (`app.data_engine.TimeframeConverter`) -> "Unknown"

`app.data_engine.TimeframeConverter.detect_timeframe` (candle-spacing
detection) is reused, not reimplemented -- the same "consume, never
rebuild" discipline every engine in this platform follows.
"""

import re
from typing import TYPE_CHECKING

import pandas as pd

from app.data_engine.columns import DATETIME_COL, TIMEFRAME_TO_PANDAS_FREQ
from app.data_engine.freq_utils import freq_to_timedelta
from app.data_engine.timeframe_converter import TimeframeConverter

if TYPE_CHECKING:
    from app.ui.state import DatasetMetadata

UNKNOWN = "Unknown"

_TOKEN_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+")

# 3-letter codes that combine pairwise into a standard 6-letter symbol
# (e.g. "EUR" + "USD" -> "EURUSD"), matched against filename tokens.
_CURRENCY_CODES = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD", "XAU", "XAG"}

# Common short tickers that map directly to a full symbol name.
_SYMBOL_ALIASES = {
    "XAU": "XAUUSD",
    "XAG": "XAGUSD",
    "BTC": "BTCUSD",
    "ETH": "ETHUSD",
    "WTI": "USOIL",
    "US30": "US30",
    "NAS100": "NAS100",
    "SPX500": "SPX500",
    "GER40": "GER40",
    "UK100": "UK100",
}

_MINUTES_PER_UNIT = {
    "m": 1, "min": 1,
    "h": 60, "hr": 60, "hour": 60,
    "d": 1440, "day": 1440,
    "w": 10080, "week": 10080,
}
_DURATION_TOKEN_RE = re.compile(r"^(\d+)(m|min|h|hr|hour|d|day|w|week)$", re.IGNORECASE)


def _tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_SPLIT_RE.split(text) if token]


def _closest_timeframe_label(minutes: float) -> str | None:
    if minutes <= 0:
        return None
    target = pd.Timedelta(minutes=minutes)
    return min(TIMEFRAME_TO_PANDAS_FREQ, key=lambda label: abs(freq_to_timedelta(TIMEFRAME_TO_PANDAS_FREQ[label]) - target))


def detect_symbol_from_filename(filename: str | None) -> str | None:
    """Best-effort symbol detection from an uploaded filename, or None if
    no recognizable symbol token is found (e.g. "XAU_5m_data.csv" -> "XAUUSD")."""
    if not filename:
        return None
    for raw in _tokens(filename):
        token = raw.upper()
        if token in _SYMBOL_ALIASES:
            return _SYMBOL_ALIASES[token]
        if len(token) == 6 and token[:3] in _CURRENCY_CODES and token[3:] in _CURRENCY_CODES:
            return token
    return None


def detect_timeframe_from_filename(filename: str | None) -> str | None:
    """Best-effort timeframe detection from an uploaded filename, or None if
    no recognizable timeframe token is found (e.g. "XAU_5m_data.csv" -> "M5")."""
    if not filename:
        return None
    for raw in _tokens(filename):
        token = raw.upper()
        if token in TIMEFRAME_TO_PANDAS_FREQ:
            return token
        match = _DURATION_TOKEN_RE.match(raw)
        if match:
            count, unit = match.groups()
            minutes = int(count) * _MINUTES_PER_UNIT[unit.lower()]
            label = _closest_timeframe_label(minutes)
            if label:
                return label
    return None


def detect_timeframe_from_datetime(df: "pd.DataFrame | None") -> str | None:
    """Best-effort timeframe detection from the modal gap between
    consecutive candle timestamps, via the shared, unmodified
    `app.data_engine.TimeframeConverter`."""
    if df is None or DATETIME_COL not in df.columns:
        return None
    return TimeframeConverter().detect_timeframe(df)


def detect_symbol(metadata: "DatasetMetadata | None", filename: str | None, df: "pd.DataFrame | None") -> str:
    """Resolve a dataset's Symbol: metadata -> filename -> DataFrame attributes -> "Unknown"."""
    if metadata is not None and metadata.symbol:
        return metadata.symbol

    from_filename = detect_symbol_from_filename(filename)
    if from_filename:
        return from_filename

    if df is not None:
        attr_symbol = df.attrs.get("symbol")
        if attr_symbol:
            return str(attr_symbol)

    return UNKNOWN


def detect_timeframe(metadata: "DatasetMetadata | None", filename: str | None, df: "pd.DataFrame | None") -> str:
    """Resolve a dataset's Timeframe: metadata -> filename -> candle spacing -> "Unknown"."""
    if metadata is not None and metadata.timeframe:
        return metadata.timeframe

    from_filename = detect_timeframe_from_filename(filename)
    if from_filename:
        return from_filename

    if metadata is not None and metadata.statistics:
        from_statistics = metadata.statistics.get("detected_timeframe")
        if from_statistics:
            return from_statistics

    from_datetime = detect_timeframe_from_datetime(df)
    if from_datetime:
        return from_datetime

    return UNKNOWN
