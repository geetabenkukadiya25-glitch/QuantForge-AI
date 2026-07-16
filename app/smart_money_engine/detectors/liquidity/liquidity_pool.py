"""Liquidity Pool detector: buy-side/sell-side resting-liquidity zones.

Composes `EqualHighDetector`/`EqualLowDetector` (clustered liquidity)
with isolated major swing points (`find_swing_highs`/`find_swing_lows`
at a longer lookback) that didn't cluster but still represent a
plausible resting-liquidity level -- reusing existing detectors instead
of duplicating their clustering logic.
"""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.liquidity.equal_high import EqualHighDetector
from app.smart_money_engine.detectors.liquidity.equal_low import EqualLowDetector
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class LiquidityPoolDetector(BaseSMCDetector):
    """Buy-side liquidity (above equal/major highs) and sell-side liquidity (below equal/major lows)."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Liquidity Pool",
            category="Liquidity",
            description="Buy-side and sell-side resting-liquidity zones from clustered and major swings.",
            inputs=("High", "Low"),
            outputs=("liquidity_pool",),
            parameters=(
                ParameterSpec("left_bars", "int", default=10, minimum=1),
                ParameterSpec("right_bars", "int", default=10, minimum=1),
                ParameterSpec("tolerance_pct", "float", default=0.05, minimum=0.0),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        tolerance_pct = self.params["tolerance_pct"]
        data = context.data

        equal_highs = EqualHighDetector(left_bars=left, right_bars=right, tolerance_pct=tolerance_pct).detect(
            context
        )
        equal_lows = EqualLowDetector(left_bars=left, right_bars=right, tolerance_pct=tolerance_pct).detect(
            context
        )
        clustered_indices = {d.index for d in equal_highs.detections} | {d.index for d in equal_lows.detections}

        detections: list[SMCDetection] = []
        for d in equal_highs.detections:
            detections.append(self._as_pool(d, "Buy-side Liquidity Pool"))
        for d in equal_lows.detections:
            detections.append(self._as_pool(d, "Sell-side Liquidity Pool"))

        for i in find_swing_highs(data, left, right):
            if i not in clustered_indices:
                detections.append(
                    SMCDetection(
                        index=i,
                        datetime=self._iso(context, i),
                        label="Buy-side Liquidity Pool",
                        price=float(data["High"].iloc[i]),
                        notes="Isolated major swing high.",
                    )
                )
        for i in find_swing_lows(data, left, right):
            if i not in clustered_indices:
                detections.append(
                    SMCDetection(
                        index=i,
                        datetime=self._iso(context, i),
                        label="Sell-side Liquidity Pool",
                        price=float(data["Low"].iloc[i]),
                        notes="Isolated major swing low.",
                    )
                )

        return sorted(detections, key=lambda d: d.index)

    @staticmethod
    def _as_pool(detection: SMCDetection, label: str) -> SMCDetection:
        return SMCDetection(
            index=detection.index,
            datetime=detection.datetime,
            end_index=detection.end_index,
            end_datetime=detection.end_datetime,
            label=label,
            price=detection.price,
            notes=detection.notes,
        )
