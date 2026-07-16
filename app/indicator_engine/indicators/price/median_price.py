"""Median Price: (High + Low) / 2."""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata


class MedianPriceIndicator(BaseIndicator):
    """Median Price: the midpoint of High and Low for each candle."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Median Price",
            category="Price",
            description="Midpoint of High and Low for each candle.",
            inputs=("High", "Low"),
            outputs=("Median_Price",),
            parameters=(),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        data = context.data
        return {"Median_Price": (data["High"] + data["Low"]) / 2}
