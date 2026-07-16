"""Equilibrium detector: the 50% midpoint of the current dealing range."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.zones._dealing_range import compute_dealing_ranges
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class EquilibriumDetector(BaseSMCDetector):
    """The 50% midpoint of the dealing range between two consecutive alternating swings."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Equilibrium",
            category="Zones",
            description="50% midpoint of the dealing range between two consecutive alternating swings.",
            inputs=("High", "Low"),
            outputs=("equilibrium",),
            parameters=(
                ParameterSpec("left_bars", "int", default=10, minimum=1),
                ParameterSpec("right_bars", "int", default=10, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        ranges = compute_dealing_ranges(context, self.params["left_bars"], self.params["right_bars"])
        return [
            SMCDetection(
                index=index,
                datetime=self._iso(context, index),
                label="Equilibrium",
                price=(top + bottom) / 2,
            )
            for index, top, bottom in ranges
        ]
