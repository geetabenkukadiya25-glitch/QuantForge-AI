"""Volume Weighted Average Price."""

import pandas as pd
from ta.volume import VolumeWeightedAveragePrice as _TaVWAP

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class VWAPIndicator(BaseIndicator):
    """Volume Weighted Average Price."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="VWAP",
            category="Volume",
            description="Volume Weighted Average Price.",
            inputs=("High", "Low", "Close", "Volume"),
            outputs=("VWAP",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaVWAP(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            volume=context.data["Volume"],
            window=self.params["window"],
        )
        return {"VWAP": result.volume_weighted_average_price()}
