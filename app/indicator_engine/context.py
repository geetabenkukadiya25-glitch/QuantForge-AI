"""The standardized input every indicator consumes.

`IndicatorContext` wraps an OHLCV DataFrame plus optional symbol/
timeframe metadata. It never carries strategy rules or execution logic
-- indicators are pure calculation components (see
`app/indicator_engine/base.py`).
"""

from dataclasses import dataclass

import pandas as pd

from app.indicator_engine.schema import DATETIME_COL


@dataclass(frozen=True)
class IndicatorContext:
    """Immutable wrapper around the OHLCV data an indicator computes over."""

    data: pd.DataFrame
    symbol: str | None = None
    timeframe: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("IndicatorContext.data must be a pandas DataFrame")

    @property
    def datetime_index(self) -> pd.Series:
        """The `Datetime` column, if present."""
        return self.data[DATETIME_COL]
