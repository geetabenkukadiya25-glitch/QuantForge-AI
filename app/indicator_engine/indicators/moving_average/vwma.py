"""Volume Weighted Moving Average.

Not provided by the `ta` library -- computed directly using the standard,
universally-agreed formula (sum(price * volume) / sum(volume) over a
rolling window). This is arithmetic, not strategy logic.
"""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class VWMAIndicator(BaseIndicator):
    """Volume Weighted Moving Average of the close price."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="VWMA",
            category="Moving Average",
            description="Volume Weighted Moving Average of the close price.",
            inputs=("Close", "Volume"),
            outputs=("VWMA",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1, description="Lookback period."),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        window = self.params["window"]
        close, volume = context.data["Close"], context.data["Volume"]
        vwma = (close * volume).rolling(window).sum() / volume.rolling(window).sum()
        return {"VWMA": vwma}
