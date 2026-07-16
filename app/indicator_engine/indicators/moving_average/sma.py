"""Simple Moving Average."""

import pandas as pd
from ta.trend import SMAIndicator as _TaSMA

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class SMAIndicator(BaseIndicator):
    """Simple Moving Average of the close price."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="SMA",
            category="Moving Average",
            description="Simple Moving Average of the close price.",
            inputs=("Close",),
            outputs=("SMA",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1, description="Lookback period."),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaSMA(close=context.data["Close"], window=self.params["window"])
        return {"SMA": result.sma_indicator()}
