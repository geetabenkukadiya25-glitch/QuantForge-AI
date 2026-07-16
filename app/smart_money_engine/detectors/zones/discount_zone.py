"""Discount Zone detector: the lower half of the current dealing range."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.zones._dealing_range import compute_dealing_ranges
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class DiscountZoneDetector(BaseSMCDetector):
    """The lower 50% of the dealing range between two consecutive alternating swings."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Discount Zone",
            category="Zones",
            description="Lower 50% of the dealing range between two consecutive alternating swings.",
            inputs=("High", "Low"),
            outputs=("discount_zone",),
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
                    label="Discount Zone",
                    top=equilibrium,
                    bottom=bottom,
                )
            )
        return detections
