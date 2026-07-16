"""Stochastic RSI."""

import pandas as pd
from ta.momentum import StochRSIIndicator as _TaStochRSI

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class StochasticRSIIndicator(BaseIndicator):
    """Stochastic oscillator applied to RSI values."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Stochastic RSI",
            category="Momentum",
            description="Stochastic oscillator applied to RSI values.",
            inputs=("Close",),
            outputs=("StochRSI", "StochRSI_K", "StochRSI_D"),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
                ParameterSpec("smooth1", "int", default=3, minimum=1),
                ParameterSpec("smooth2", "int", default=3, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaStochRSI(
            close=context.data["Close"],
            window=self.params["window"],
            smooth1=self.params["smooth1"],
            smooth2=self.params["smooth2"],
        )
        return {
            "StochRSI": result.stochrsi(),
            "StochRSI_K": result.stochrsi_k(),
            "StochRSI_D": result.stochrsi_d(),
        }
