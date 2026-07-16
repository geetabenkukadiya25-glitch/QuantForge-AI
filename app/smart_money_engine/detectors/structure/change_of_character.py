"""Change of Character (CHoCH) detector.

A CHoCH is a *reversal* break: price closes beyond the most recent swing
extreme in the opposite direction of the already-established trend --
the first structural sign a trend may be reversing. Shares its scan with
`BOSDetector` via `_structure_breaks.scan_structure_breaks`.
"""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.structure._structure_breaks import scan_structure_breaks
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class CHoCHDetector(BaseSMCDetector):
    """Reversal break of the most recent swing extreme, against the established trend."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Change Of Character",
            category="Structure",
            description="Reversal break of the most recent swing extreme, against the established trend.",
            inputs=("High", "Low", "Close"),
            outputs=("choch",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        breaks = scan_structure_breaks(context, self.params["left_bars"], self.params["right_bars"])
        return [b for b in breaks if "CHoCH" in b.label]
