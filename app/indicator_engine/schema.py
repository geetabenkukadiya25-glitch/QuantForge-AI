"""Input data contract for the Indicator Engine.

Indicators consume standardized OHLCV data only -- never strategy rules,
never execution logic. Intentionally a separate, self-contained
convention from `app.data_engine`/`app.chart_engine` (same architectural
trade-off documented in both of those modules): each engine defines its
own minimal contract rather than importing a sibling engine's schema.
"""

import pandas as pd

from app.indicator_engine.exceptions import IndicatorEngineError

DATETIME_COL = "Datetime"
OHLC_COLS = ["Open", "High", "Low", "Close"]
VOLUME_COL = "Volume"

STANDARD_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL]


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise `IndicatorEngineError` if `df` is missing any of `columns`."""
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise IndicatorEngineError(f"Missing required column(s): {missing}")
    if df.empty:
        raise IndicatorEngineError("Cannot compute an indicator over an empty DataFrame.")
