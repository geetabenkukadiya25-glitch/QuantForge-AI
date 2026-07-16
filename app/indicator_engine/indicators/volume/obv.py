"""On-Balance Volume."""

import pandas as pd
from ta.volume import OnBalanceVolumeIndicator as _TaOBV

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata


class OBVIndicator(BaseIndicator):
    """On-Balance Volume: cumulative volume flow."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="OBV",
            category="Volume",
            description="On-Balance Volume (cumulative volume flow).",
            inputs=("Close", "Volume"),
            outputs=("OBV",),
            parameters=(),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaOBV(close=context.data["Close"], volume=context.data["Volume"])
        return {"OBV": result.on_balance_volume()}
