"""Order Block detector: the last opposite-colored candle before a displacement move."""

import pandas as pd

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import average_range
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class OrderBlockDetector(BaseSMCDetector):
    """The last down-candle before a strong up-move (or last up-candle before a strong down-move)."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Order Block",
            category="Blocks",
            description="Last opposite-colored candle before a displacement move in the other direction.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("order_block",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1, description="Average-range window."),
                ParameterSpec("multiplier", "float", default=2.0, minimum=0.0, description="Displacement threshold."),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        data = context.data
        window, multiplier = self.params["window"], self.params["multiplier"]
        avg_range = average_range(data, window)
        candle_range = data["High"] - data["Low"]
        bullish = data["Close"] > data["Open"]
        bearish = data["Close"] < data["Open"]

        detections: list[SMCDetection] = []
        seen_indices: set[int] = set()
        for i in range(window, len(data)):
            baseline = avg_range.iloc[i - 1]
            if pd.isna(baseline) or candle_range.iloc[i] <= baseline * multiplier:
                continue

            if bullish.iloc[i]:
                j = self._find_last(bearish, i)
                label, direction = "Bullish Order Block", "bullish"
            elif bearish.iloc[i]:
                j = self._find_last(bullish, i)
                label, direction = "Bearish Order Block", "bearish"
            else:
                continue

            if j is None or j in seen_indices:
                continue
            seen_indices.add(j)
            detections.append(
                SMCDetection(
                    index=j,
                    datetime=self._iso(context, j),
                    end_index=i,
                    end_datetime=self._iso(context, i),
                    label=label,
                    direction=direction,
                    top=float(data["High"].iloc[j]),
                    bottom=float(data["Low"].iloc[j]),
                    notes="Last opposite-colored candle before a displacement move.",
                )
            )
        return sorted(detections, key=lambda d: d.index)

    @staticmethod
    def _find_last(mask: pd.Series, before_index: int) -> int | None:
        for j in range(before_index - 1, -1, -1):
            if mask.iloc[j]:
                return j
        return None
