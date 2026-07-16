"""Parabolic SAR (Stop and Reverse)."""

import pandas as pd
from ta.trend import PSARIndicator as _TaPSAR

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class ParabolicSARIndicator(BaseIndicator):
    """Parabolic Stop-And-Reverse trailing price level."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Parabolic SAR",
            category="Trend",
            description="Parabolic Stop-And-Reverse trailing price level.",
            inputs=("High", "Low", "Close"),
            outputs=("PSAR",),
            parameters=(
                ParameterSpec("step", "float", default=0.02, minimum=0.0),
                ParameterSpec("max_step", "float", default=0.2, minimum=0.0),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaPSAR(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            step=self.params["step"],
            max_step=self.params["max_step"],
        )
        return {"PSAR": result.psar()}
