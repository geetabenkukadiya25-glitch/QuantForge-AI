"""Breaker Block detector: an order block that gets violated and flips role."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.blocks.order_block import OrderBlockDetector
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class BreakerBlockDetector(BaseSMCDetector):
    """An order block whose zone is later violated by a close through it, flipping its role."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Breaker Block",
            category="Blocks",
            description="An order block later violated by a close through its zone, flipping its role.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("breaker_block",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
                ParameterSpec("multiplier", "float", default=2.0, minimum=0.0),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        order_blocks = OrderBlockDetector(
            window=self.params["window"], multiplier=self.params["multiplier"]
        ).detect(context)

        detections: list[SMCDetection] = []
        for ob in order_blocks.detections:
            violation_index = self._find_violation(context, ob)
            if violation_index is None:
                continue
            is_bullish_ob = ob.direction == "bullish"
            detections.append(
                SMCDetection(
                    index=violation_index,
                    datetime=self._iso(context, violation_index),
                    label="Bearish Breaker Block" if is_bullish_ob else "Bullish Breaker Block",
                    direction="bearish" if is_bullish_ob else "bullish",
                    top=ob.top,
                    bottom=ob.bottom,
                    notes=f"Order block at index {ob.index} was violated and now acts as a breaker.",
                )
            )
        return sorted(detections, key=lambda d: d.index)

    @staticmethod
    def _find_violation(context: SMCContext, order_block: SMCDetection) -> int | None:
        data = context.data
        start = (order_block.end_index if order_block.end_index is not None else order_block.index) + 1
        for i in range(start, len(data)):
            close = float(data["Close"].iloc[i])
            if order_block.direction == "bullish" and close < order_block.bottom:
                return i
            if order_block.direction == "bearish" and close > order_block.top:
                return i
        return None
