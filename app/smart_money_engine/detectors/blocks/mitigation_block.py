"""Mitigation Block detector: the last opposite candle before a swing reversal.

Distinct from `OrderBlockDetector` in that it doesn't require a strong
displacement move -- only a confirmed swing point -- making it a weaker,
more frequent structural zone.
"""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class MitigationBlockDetector(BaseSMCDetector):
    """Last opposite-colored candle immediately before a confirmed swing point."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Mitigation Block",
            category="Blocks",
            description="Last opposite-colored candle immediately before a confirmed swing point.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("mitigation_block",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        data = context.data
        left, right = self.params["left_bars"], self.params["right_bars"]
        bullish = data["Close"] > data["Open"]
        bearish = data["Close"] < data["Open"]

        detections: list[SMCDetection] = []
        seen: set[int] = set()
        for i in find_swing_highs(data, left, right):
            j = self._find_last(bullish, i)
            if j is not None and j not in seen:
                seen.add(j)
                detections.append(self._build(context, j, "Bearish Mitigation Block", "bearish"))
        for i in find_swing_lows(data, left, right):
            j = self._find_last(bearish, i)
            if j is not None and j not in seen:
                seen.add(j)
                detections.append(self._build(context, j, "Bullish Mitigation Block", "bullish"))
        return sorted(detections, key=lambda d: d.index)

    def _build(self, context: SMCContext, index: int, label: str, direction: str) -> SMCDetection:
        data = context.data
        return SMCDetection(
            index=index,
            datetime=self._iso(context, index),
            label=label,
            direction=direction,
            top=float(data["High"].iloc[index]),
            bottom=float(data["Low"].iloc[index]),
            notes="Last opposite-colored candle before a confirmed swing point.",
        )

    @staticmethod
    def _find_last(mask, before_index: int) -> int | None:
        for j in range(before_index - 1, -1, -1):
            if mask.iloc[j]:
                return j
        return None
