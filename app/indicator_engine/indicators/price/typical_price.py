"""Typical Price: (High + Low + Close) / 3."""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata


class TypicalPriceIndicator(BaseIndicator):
    """Typical Price: the average of High, Low, and Close for each candle."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Typical Price",
            category="Price",
            description="Average of High, Low, and Close for each candle.",
            inputs=("High", "Low", "Close"),
            outputs=("Typical_Price",),
            parameters=(),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        data = context.data
        return {"Typical_Price": (data["High"] + data["Low"] + data["Close"]) / 3}
