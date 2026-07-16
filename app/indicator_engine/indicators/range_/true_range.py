"""True Range: max(High-Low, |High-PrevClose|, |Low-PrevClose|)."""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata


class TrueRangeIndicator(BaseIndicator):
    """True Range: the greatest of the three standard candle-range measures."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="True Range",
            category="Range",
            description="Greatest of High-Low, |High-PrevClose|, and |Low-PrevClose|.",
            inputs=("High", "Low", "Close"),
            outputs=("True_Range",),
            parameters=(),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        data = context.data
        prev_close = data["Close"].shift(1)
        ranges = pd.concat(
            [
                data["High"] - data["Low"],
                (data["High"] - prev_close).abs(),
                (data["Low"] - prev_close).abs(),
            ],
            axis=1,
        )
        return {"True_Range": ranges.max(axis=1)}
