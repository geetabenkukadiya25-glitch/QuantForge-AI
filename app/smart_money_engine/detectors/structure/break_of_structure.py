"""Break of Structure (BOS) detector.

A BOS is a *continuation* break: price closes beyond the most recent
swing extreme in the direction of the already-established trend. A
break in the opposite direction of the established trend is a Change of
Character instead (see `change_of_character.py`) -- both detectors
share the same underlying scan, implemented once in `_scan_breaks`.
"""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.structure._structure_breaks import scan_structure_breaks
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class BOSDetector(BaseSMCDetector):
    """Continuation break of the most recent swing extreme in the trend's direction."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Break Of Structure",
            category="Structure",
            description="Continuation break of the most recent swing extreme, in the trend's direction.",
            inputs=("High", "Low", "Close"),
            outputs=("bos",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        breaks = scan_structure_breaks(context, self.params["left_bars"], self.params["right_bars"])
        return [b for b in breaks if b.label.startswith("Bullish BOS") or b.label.startswith("Bearish BOS")]
