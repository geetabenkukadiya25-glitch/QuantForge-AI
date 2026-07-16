"""The standardized input every Smart Money detector consumes.

`SMCContext` wraps an OHLCV DataFrame plus optional symbol/timeframe
metadata -- the same minimal contract `app.indicator_engine.IndicatorContext`
uses. It additionally carries two *optional* fields so detectors can use
Data Engine, Context Engine, and Indicator Engine outputs where
appropriate (per the Phase 7 spec):

- `indicators`: a bag of precomputed `IndicatorResult`s (e.g. an ATR
  result a displacement detector can use instead of recomputing its own
  volatility measure).
- `context_snapshot`: an optional `ContextSnapshot` from the Market
  Context Engine.

Never carries strategy rules or execution logic.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.context_engine.models import ContextSnapshot
from app.indicator_engine.result import IndicatorResult
from app.smart_money_engine.schema import DATETIME_COL


@dataclass(frozen=True)
class SMCContext:
    """Immutable wrapper around the OHLCV data (+ optional context) a detector runs over."""

    data: pd.DataFrame
    symbol: str | None = None
    timeframe: str | None = None
    indicators: dict[str, IndicatorResult] = field(default_factory=dict)
    context_snapshot: ContextSnapshot | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.data, pd.DataFrame):
            raise TypeError("SMCContext.data must be a pandas DataFrame")

    @property
    def datetime_index(self) -> pd.Series:
        """The `Datetime` column, if present."""
        return self.data[DATETIME_COL]
