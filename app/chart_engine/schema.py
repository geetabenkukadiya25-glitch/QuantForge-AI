"""Input data contract for the chart engine.

The chart engine deliberately does not import `app.data_engine` -- it
only expects a plain pandas DataFrame following this column convention,
so it can be fed by the data engine, a future live feed, or a hand-built
DataFrame in a test, without a hard dependency on any of them.
"""

import pandas as pd

from app.chart_engine.exceptions import ChartDataError

DATETIME_COL = "Datetime"
OHLC_COLS = ["Open", "High", "Low", "Close"]
VOLUME_COL = "Volume"
SPREAD_COL = "Spread"

REQUIRED_COLUMNS = [DATETIME_COL, *OHLC_COLS]


def validate_ohlcv(df: pd.DataFrame) -> None:
    """Raise `ChartDataError` if `df` lacks the columns required to chart it."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ChartDataError(f"Cannot chart data: missing column(s) {missing}")
    if df.empty:
        raise ChartDataError("Cannot chart data: DataFrame is empty")
