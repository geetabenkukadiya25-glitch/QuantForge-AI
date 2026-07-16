"""Bollinger Bands."""

import pandas as pd
from ta.volatility import BollingerBands as _TaBollinger

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands: moving average with upper/lower standard-deviation bands."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Bollinger Bands",
            category="Volatility",
            description="Moving average with upper/lower standard-deviation bands.",
            inputs=("Close",),
            outputs=("BB_Middle", "BB_Upper", "BB_Lower"),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1),
                ParameterSpec("window_dev", "int", default=2, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaBollinger(
            close=context.data["Close"],
            window=self.params["window"],
            window_dev=self.params["window_dev"],
        )
        return {
            "BB_Middle": result.bollinger_mavg(),
            "BB_Upper": result.bollinger_hband(),
            "BB_Lower": result.bollinger_lband(),
        }
