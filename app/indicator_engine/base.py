"""Abstract base class every indicator implements.

An indicator is a pure calculation component: given an `IndicatorContext`
(OHLCV data), it returns an `IndicatorResult`. It never generates
buy/sell signals, never contains strategy logic, and never executes
trades -- interpretation of indicator values is a future engine's job.
"""

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata
from app.indicator_engine.result import INDICATOR_RESULT_VERSION, IndicatorResult
from app.indicator_engine.schema import DATETIME_COL


class BaseIndicator(ABC):
    """Common contract every indicator implementation satisfies."""

    def __init__(self, **params: Any) -> None:
        metadata = self.metadata()
        self.params: dict[str, Any] = {**metadata.default_params(), **params}

    @classmethod
    @abstractmethod
    def metadata(cls) -> IndicatorMetadata:
        """Return this indicator's static description (name, category, inputs,
        outputs, parameters, version)."""

    @abstractmethod
    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        """Compute the indicator's raw output series.

        Subclasses implement only this; `compute()` wraps the result into
        a standardized, immutable `IndicatorResult`.
        """

    def compute(self, context: IndicatorContext) -> IndicatorResult:
        """Run the indicator over `context` and return an `IndicatorResult`."""
        metadata = self.metadata()
        raw = self._calculate(context)

        datetime_index = tuple(
            value.isoformat() if hasattr(value, "isoformat") else str(value)
            for value in context.data[DATETIME_COL]
        )
        values = {
            name: tuple(None if pd.isna(v) else float(v) for v in series)
            for name, series in raw.items()
        }

        return IndicatorResult(
            indicator_name=metadata.name,
            category=metadata.category,
            indicator_version=metadata.version,
            result_version=INDICATOR_RESULT_VERSION,
            symbol=context.symbol,
            timeframe=context.timeframe,
            parameters=dict(self.params),
            datetime_index=datetime_index,
            values=values,
        )
