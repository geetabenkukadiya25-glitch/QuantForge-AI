"""Average Directional Index."""

import pandas as pd
from ta.trend import ADXIndicator as _TaADX

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class ADXIndicator(BaseIndicator):
    """Average Directional Index: trend strength, plus +DI/-DI."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="ADX",
            category="Trend",
            description="Average Directional Index (trend strength).",
            inputs=("High", "Low", "Close"),
            outputs=("ADX", "ADX_Pos", "ADX_Neg"),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaADX(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            window=self.params["window"],
        )
        return {
            "ADX": result.adx(),
            "ADX_Pos": result.adx_pos(),
            "ADX_Neg": result.adx_neg(),
        }
