"""Keltner Channels."""

import pandas as pd
from ta.volatility import KeltnerChannel as _TaKeltner

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class KeltnerChannelsIndicator(BaseIndicator):
    """Keltner Channels: EMA with ATR-based upper/lower bands."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Keltner Channels",
            category="Volatility",
            description="EMA with ATR-based upper/lower bands.",
            inputs=("High", "Low", "Close"),
            outputs=("KC_Middle", "KC_Upper", "KC_Lower"),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1),
                ParameterSpec("window_atr", "int", default=10, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaKeltner(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            window=self.params["window"],
            window_atr=self.params["window_atr"],
        )
        return {
            "KC_Middle": result.keltner_channel_mband(),
            "KC_Upper": result.keltner_channel_hband(),
            "KC_Lower": result.keltner_channel_lband(),
        }
