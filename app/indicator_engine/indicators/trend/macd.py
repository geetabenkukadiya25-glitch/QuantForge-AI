"""Moving Average Convergence Divergence."""

import pandas as pd
from ta.trend import MACD as _TaMACD

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class MACDIndicator(BaseIndicator):
    """Moving Average Convergence Divergence: line, signal, and histogram."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="MACD",
            category="Trend",
            description="Moving Average Convergence Divergence.",
            inputs=("Close",),
            outputs=("MACD", "MACD_Signal", "MACD_Histogram"),
            parameters=(
                ParameterSpec("window_fast", "int", default=12, minimum=1),
                ParameterSpec("window_slow", "int", default=26, minimum=1),
                ParameterSpec("window_sign", "int", default=9, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaMACD(
            close=context.data["Close"],
            window_fast=self.params["window_fast"],
            window_slow=self.params["window_slow"],
            window_sign=self.params["window_sign"],
        )
        return {
            "MACD": result.macd(),
            "MACD_Signal": result.macd_signal(),
            "MACD_Histogram": result.macd_diff(),
        }
