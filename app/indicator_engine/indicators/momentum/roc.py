"""Rate of Change."""

import pandas as pd
from ta.momentum import ROCIndicator as _TaROC

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class ROCIndicator(BaseIndicator):
    """Rate of Change: percentage price change over `window` periods."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="ROC",
            category="Momentum",
            description="Rate of Change (percentage price change over the lookback window).",
            inputs=("Close",),
            outputs=("ROC",),
            parameters=(
                ParameterSpec("window", "int", default=12, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaROC(close=context.data["Close"], window=self.params["window"])
        return {"ROC": result.roc()}
