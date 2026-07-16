"""Weighted Moving Average."""

import pandas as pd
from ta.trend import WMAIndicator as _TaWMA

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class WMAIndicator(BaseIndicator):
    """Weighted Moving Average of the close price (linear weights)."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="WMA",
            category="Moving Average",
            description="Weighted Moving Average of the close price (linear weights).",
            inputs=("Close",),
            outputs=("WMA",),
            parameters=(
                ParameterSpec("window", "int", default=9, minimum=1, description="Lookback period."),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaWMA(close=context.data["Close"], window=self.params["window"])
        return {"WMA": result.wma()}
