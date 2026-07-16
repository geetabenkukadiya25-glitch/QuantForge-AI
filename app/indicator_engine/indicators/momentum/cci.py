"""Commodity Channel Index."""

import pandas as pd
from ta.trend import CCIIndicator as _TaCCI

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class CCIIndicator(BaseIndicator):
    """Commodity Channel Index."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="CCI",
            category="Momentum",
            description="Commodity Channel Index.",
            inputs=("High", "Low", "Close"),
            outputs=("CCI",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1),
                ParameterSpec("constant", "float", default=0.015, minimum=0.0),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaCCI(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            window=self.params["window"],
            constant=self.params["constant"],
        )
        return {"CCI": result.cci()}
