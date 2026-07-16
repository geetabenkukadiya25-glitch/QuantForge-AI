"""Weighted Close: (High + Low + 2 * Close) / 4."""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata


class WeightedCloseIndicator(BaseIndicator):
    """Weighted Close: Close weighted twice as heavily as High/Low."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Weighted Close",
            category="Price",
            description="Close weighted twice as heavily as High/Low.",
            inputs=("High", "Low", "Close"),
            outputs=("Weighted_Close",),
            parameters=(),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        data = context.data
        return {"Weighted_Close": (data["High"] + data["Low"] + 2 * data["Close"]) / 4}
