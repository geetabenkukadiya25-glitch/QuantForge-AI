"""Internal Structure detector: minor swing points using a short lookback window."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class InternalStructureDetector(BaseSMCDetector):
    """Minor swing highs/lows detected with a short lookback window.

    Internal structure captures short-term pivots within the broader
    trend, as distinct from `ExternalStructureDetector`'s major swings.
    """

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Internal Structure",
            category="Structure",
            description="Minor swing highs/lows within the broader trend (short lookback window).",
            inputs=("High", "Low"),
            outputs=("internal_structure",),
            parameters=(
                ParameterSpec("left_bars", "int", default=2, minimum=1),
                ParameterSpec("right_bars", "int", default=2, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        data = context.data
        detections = [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="Internal Structure High",
                price=float(data["High"].iloc[i]),
            )
            for i in find_swing_highs(data, left, right)
        ]
        detections += [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="Internal Structure Low",
                price=float(data["Low"].iloc[i]),
            )
            for i in find_swing_lows(data, left, right)
        ]
        return sorted(detections, key=lambda d: d.index)
