"""Chaikin Money Flow."""

import pandas as pd
from ta.volume import ChaikinMoneyFlowIndicator as _TaCMF

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class ChaikinMoneyFlowIndicator(BaseIndicator):
    """Chaikin Money Flow: volume-weighted accumulation/distribution."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Chaikin Money Flow",
            category="Volume",
            description="Volume-weighted accumulation/distribution over a rolling window.",
            inputs=("High", "Low", "Close", "Volume"),
            outputs=("CMF",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaCMF(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            volume=context.data["Volume"],
            window=self.params["window"],
        )
        return {"CMF": result.chaikin_money_flow()}
