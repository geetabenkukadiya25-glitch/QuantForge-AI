"""External Structure detector: major swing points using a long lookback window."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class ExternalStructureDetector(BaseSMCDetector):
    """Major swing highs/lows detected with a long lookback window.

    External structure captures the broader trend's defining swings, as
    distinct from `InternalStructureDetector`'s minor pivots.
    """

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="External Structure",
            category="Structure",
            description="Major swing highs/lows defining the broader trend (long lookback window).",
            inputs=("High", "Low"),
            outputs=("external_structure",),
            parameters=(
                ParameterSpec("left_bars", "int", default=10, minimum=1),
                ParameterSpec("right_bars", "int", default=10, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        data = context.data
        detections = [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="External Structure High",
                price=float(data["High"].iloc[i]),
            )
            for i in find_swing_highs(data, left, right)
        ]
        detections += [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="External Structure Low",
                price=float(data["Low"].iloc[i]),
            )
            for i in find_swing_lows(data, left, right)
        ]
        return sorted(detections, key=lambda d: d.index)
