"""Retracement detector: how far price pulls back into a prior impulse move."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.momentum.impulse_move import ImpulseMoveDetector
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class RetracementDetector(BaseSMCDetector):
    """The percentage pullback into the most recent impulse move at the next opposing swing."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Retracement",
            category="Momentum",
            description="Percentage pullback into the most recent impulse move at the next opposing swing.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("retracement",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
                ParameterSpec("multiplier", "float", default=2.0, minimum=0.0),
                ParameterSpec("min_candles", "int", default=2, minimum=1),
                ParameterSpec("left_bars", "int", default=3, minimum=1),
                ParameterSpec("right_bars", "int", default=3, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        impulses = ImpulseMoveDetector(
            window=self.params["window"],
            multiplier=self.params["multiplier"],
            min_candles=self.params["min_candles"],
        ).detect(context).detections

        left, right = self.params["left_bars"], self.params["right_bars"]
        data = context.data
        swing_highs = set(find_swing_highs(data, left, right))
        swing_lows = set(find_swing_lows(data, left, right))

        detections: list[SMCDetection] = []
        for impulse in impulses:
            pullback_index = self._find_pullback(impulse, swing_highs, swing_lows)
            if pullback_index is None:
                continue
            impulse_start = impulse.bottom if impulse.direction == "bullish" else impulse.top
            impulse_end = impulse.top if impulse.direction == "bullish" else impulse.bottom
            pullback_price = float(
                data["Low"].iloc[pullback_index] if impulse.direction == "bullish" else data["High"].iloc[pullback_index]
            )
            impulse_range = impulse_end - impulse_start
            if impulse_range == 0:
                continue
            retracement_pct = abs(impulse_end - pullback_price) / abs(impulse_range) * 100
            detections.append(
                SMCDetection(
                    index=pullback_index,
                    datetime=self._iso(context, pullback_index),
                    label="Retracement",
                    direction=impulse.direction,
                    price=pullback_price,
                    notes=f"{retracement_pct:.1f}% retracement into the impulse move at index {impulse.index}.",
                )
            )
        return detections

    @staticmethod
    def _find_pullback(impulse, swing_highs: set[int], swing_lows: set[int]) -> int | None:
        candidates = swing_lows if impulse.direction == "bullish" else swing_highs
        after_impulse = sorted(i for i in candidates if i > (impulse.end_index or impulse.index))
        return after_impulse[0] if after_impulse else None
