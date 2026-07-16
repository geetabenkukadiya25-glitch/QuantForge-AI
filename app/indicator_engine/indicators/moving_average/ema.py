"""Exponential Moving Average."""

import pandas as pd
from ta.trend import EMAIndicator as _TaEMA

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class EMAIndicator(BaseIndicator):
    """Exponential Moving Average of the close price."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="EMA",
            category="Moving Average",
            description="Exponential Moving Average of the close price.",
            inputs=("Close",),
            outputs=("EMA",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1, description="Lookback period."),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaEMA(close=context.data["Close"], window=self.params["window"])
        return {"EMA": result.ema_indicator()}
