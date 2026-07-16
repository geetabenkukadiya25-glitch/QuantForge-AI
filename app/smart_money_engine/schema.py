"""Input data contract for the Smart Money Engine.

Detectors consume standardized OHLCV data only -- never strategy rules,
never execution logic. Intentionally a separate, self-contained
convention from sibling engines (`app.data_engine`, `app.chart_engine`,
`app.indicator_engine`), matching the same architectural trade-off
documented throughout the codebase.
"""

import pandas as pd

from app.smart_money_engine.exceptions import SMCEngineError

DATETIME_COL = "Datetime"
OHLC_COLS = ["Open", "High", "Low", "Close"]
VOLUME_COL = "Volume"

STANDARD_COLUMNS = [DATETIME_COL, *OHLC_COLS, VOLUME_COL]


def require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    """Raise `SMCEngineError` if `df` is missing any of `columns`."""
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise SMCEngineError(f"Missing required column(s): {missing}")
    if df.empty:
        raise SMCEngineError("Cannot run a detector over an empty DataFrame.")
