"""Swing Low detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_lows
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class SwingLowDetector(BaseSMCDetector):
    """A candle whose Low is the strict minimum within a symmetric lookback window."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Swing Low",
            category="Structure",
            description="A candle whose Low is the strict minimum within a symmetric lookback window.",
            inputs=("Low",),
            outputs=("swing_low",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        indices = find_swing_lows(context.data, self.params["left_bars"], self.params["right_bars"])
        return [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="Swing Low",
                price=float(context.data["Low"].iloc[i]),
            )
            for i in indices
        ]
