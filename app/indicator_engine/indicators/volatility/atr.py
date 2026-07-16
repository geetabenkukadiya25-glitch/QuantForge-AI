"""Average True Range."""

import pandas as pd
from ta.volatility import AverageTrueRange as _TaATR

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class ATRIndicator(BaseIndicator):
    """Average True Range: smoothed measure of price volatility."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="ATR",
            category="Volatility",
            description="Average True Range.",
            inputs=("High", "Low", "Close"),
            outputs=("ATR",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaATR(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            window=self.params["window"],
        )
        return {"ATR": result.average_true_range()}
