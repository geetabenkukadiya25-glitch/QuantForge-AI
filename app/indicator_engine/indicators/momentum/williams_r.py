"""Williams %R."""

import pandas as pd
from ta.momentum import WilliamsRIndicator as _TaWilliamsR

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class WilliamsRIndicator(BaseIndicator):
    """Williams %R momentum oscillator."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Williams %R",
            category="Momentum",
            description="Williams %R momentum oscillator.",
            inputs=("High", "Low", "Close"),
            outputs=("Williams_R",),
            parameters=(
                ParameterSpec("lbp", "int", default=14, minimum=1, description="Lookback period."),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaWilliamsR(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            lbp=self.params["lbp"],
        )
        return {"Williams_R": result.williams_r()}
