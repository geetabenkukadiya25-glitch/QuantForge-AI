"""Swing High detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class SwingHighDetector(BaseSMCDetector):
    """A candle whose High is the strict maximum within a symmetric lookback window."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Swing High",
            category="Structure",
            description="A candle whose High is the strict maximum within a symmetric lookback window.",
            inputs=("High",),
            outputs=("swing_high",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        indices = find_swing_highs(context.data, self.params["left_bars"], self.params["right_bars"])
        return [
            SMCDetection(
                index=i,
                datetime=self._iso(context, i),
                label="Swing High",
                price=float(context.data["High"].iloc[i]),
            )
            for i in indices
        ]
