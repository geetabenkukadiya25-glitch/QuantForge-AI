"""Relative Strength Index."""

import pandas as pd
from ta.momentum import RSIIndicator as _TaRSI

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class RSIIndicator(BaseIndicator):
    """Relative Strength Index."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="RSI",
            category="Momentum",
            description="Relative Strength Index.",
            inputs=("Close",),
            outputs=("RSI",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaRSI(close=context.data["Close"], window=self.params["window"])
        return {"RSI": result.rsi()}
