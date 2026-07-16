"""Money Flow Index."""

import pandas as pd
from ta.volume import MFIIndicator as _TaMFI

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class MFIIndicator(BaseIndicator):
    """Money Flow Index: volume-weighted RSI."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="MFI",
            category="Volume",
            description="Money Flow Index (volume-weighted RSI).",
            inputs=("High", "Low", "Close", "Volume"),
            outputs=("MFI",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        result = _TaMFI(
            high=context.data["High"],
            low=context.data["Low"],
            close=context.data["Close"],
            volume=context.data["Volume"],
            window=self.params["window"],
        )
        return {"MFI": result.money_flow_index()}
