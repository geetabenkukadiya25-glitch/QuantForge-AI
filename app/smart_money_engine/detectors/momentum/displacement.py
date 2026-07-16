"""Displacement detector: an unusually large candle signaling aggressive participation.

Demonstrates optional Indicator Engine consumption (per the Phase 7
spec's "use ... Indicator Engine outputs where appropriate"): if
`context.indicators` carries a precomputed `"ATR"` `IndicatorResult`, its
values are used as the volatility baseline instead of a locally computed
rolling range.
"""

import pandas as pd

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import average_range
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class DisplacementDetector(BaseSMCDetector):
    """A candle whose range greatly exceeds the recent average (or ATR) baseline."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Displacement",
            category="Momentum",
            description="A candle whose range greatly exceeds the recent average (or ATR) baseline.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("displacement",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1, description="Baseline window (if no ATR given)."),
                ParameterSpec("multiplier", "float", default=2.0, minimum=0.0),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        data = context.data
        multiplier = self.params["multiplier"]
        baseline = self._baseline(context)
        candle_range = data["High"] - data["Low"]

        detections: list[SMCDetection] = []
        for i in range(len(data)):
            base = baseline.iloc[i - 1] if i > 0 else None
            if base is None or pd.isna(base) or candle_range.iloc[i] <= base * multiplier:
                continue
            is_bullish = float(data["Close"].iloc[i]) > float(data["Open"].iloc[i])
            detections.append(
                SMCDetection(
                    index=i,
                    datetime=self._iso(context, i),
                    label="Bullish Displacement" if is_bullish else "Bearish Displacement",
                    direction="bullish" if is_bullish else "bearish",
                    top=float(data["High"].iloc[i]),
                    bottom=float(data["Low"].iloc[i]),
                )
            )
        return detections

    def _baseline(self, context: SMCContext) -> pd.Series:
        atr_result = context.indicators.get("ATR")
        if atr_result is not None:
            values = [v if v is not None else float("nan") for v in atr_result.values["ATR"]]
            return pd.Series(values, index=context.data.index)
        return average_range(context.data, self.params["window"])
