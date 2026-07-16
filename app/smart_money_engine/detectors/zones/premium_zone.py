"""Premium Zone detector: the upper half of the current dealing range."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.zones._dealing_range import compute_dealing_ranges
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PremiumZoneDetector(BaseSMCDetector):
    """The upper 50% of the dealing range between two consecutive alternating swings."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Premium Zone",
            category="Zones",
            description="Upper 50% of the dealing range between two consecutive alternating swings.",
            inputs=("High", "Low"),
            outputs=("premium_zone",),
            parameters=(
                ParameterSpec("left_bars", "int", default=10, minimum=1),
                ParameterSpec("right_bars", "int", default=10, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        ranges = compute_dealing_ranges(context, self.params["left_bars"], self.params["right_bars"])
        detections = []
        for index, top, bottom in ranges:
            equilibrium = (top + bottom) / 2
            detections.append(
                SMCDetection(
                    index=index,
                    datetime=self._iso(context, index),
                    label="Premium Zone",
                    top=top,
                    bottom=equilibrium,
                )
            )
        return detections
