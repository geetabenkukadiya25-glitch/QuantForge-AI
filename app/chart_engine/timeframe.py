"""Timeframe support for the chart engine.

Deliberately self-contained (no import of `app.data_engine`) so the
chart engine has no hard dependency on the data engine's internals --
see `app/chart_engine/schema.py` for the rationale.
"""

import pandas as pd

from app.chart_engine.exceptions import ChartEngineError
from app.chart_engine.schema import DATETIME_COL, SPREAD_COL, VOLUME_COL

TIMEFRAMES: list[str] = ["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"]

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


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """Resample a standard-schema OHLCV DataFrame to `timeframe` (e.g. "H4").

    Raises:
        ChartEngineError: if `timeframe` is not a recognized label.
    """
    freq = TIMEFRAME_TO_PANDAS_FREQ.get(timeframe)
    if freq is None:
        raise ChartEngineError(f"Unknown timeframe label: {timeframe!r}")

    agg: dict[str, str] = {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    if VOLUME_COL in df.columns:
        agg[VOLUME_COL] = "sum"
    if SPREAD_COL in df.columns:
        agg[SPREAD_COL] = "mean"

    indexed = df.set_index(DATETIME_COL).sort_index()
    resampled = indexed.resample(freq).agg(agg).dropna(subset=["Open", "High", "Low", "Close"])
    return resampled.reset_index()
