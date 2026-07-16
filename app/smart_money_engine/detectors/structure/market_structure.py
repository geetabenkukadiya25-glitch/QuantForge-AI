"""Market Structure detector: classifies swing points as HH/HL/LH/LL."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class MarketStructureDetector(BaseSMCDetector):
    """Labels each confirmed swing point relative to the prior swing of the same type.

    A swing high becomes a "Higher High" or "Lower High" depending on
    whether it exceeds the previous swing high; a swing low becomes a
    "Higher Low" or "Lower Low" similarly.
    """

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Market Structure",
            category="Structure",
            description="Classifies swing points as Higher High / Higher Low / Lower High / Lower Low.",
            inputs=("High", "Low"),
            outputs=("market_structure",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        data = context.data
        highs = [(i, float(data["High"].iloc[i]), "high") for i in find_swing_highs(data, left, right)]
        lows = [(i, float(data["Low"].iloc[i]), "low") for i in find_swing_lows(data, left, right)]
        swings = sorted(highs + lows, key=lambda item: item[0])

        detections: list[SMCDetection] = []
        last_high: float | None = None
        last_low: float | None = None
        for index, price, kind in swings:
            if kind == "high":
                if last_high is not None:
                    label = "Higher High" if price > last_high else "Lower High"
                    detections.append(
                        SMCDetection(
                            index=index,
                            datetime=self._iso(context, index),
                            label=label,
                            direction="bullish" if label == "Higher High" else "bearish",
                            price=price,
                        )
                    )
                last_high = price
            else:
                if last_low is not None:
                    label = "Higher Low" if price > last_low else "Lower Low"
                    detections.append(
                        SMCDetection(
                            index=index,
                            datetime=self._iso(context, index),
                            label=label,
                            direction="bullish" if label == "Higher Low" else "bearish",
                            price=price,
                        )
                    )
                last_low = price
        return detections
