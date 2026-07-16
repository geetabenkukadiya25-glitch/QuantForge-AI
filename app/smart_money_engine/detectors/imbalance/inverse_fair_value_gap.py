"""Inverse Fair Value Gap (IFVG) detector: a Fair Value Gap fully filled by later price action."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.imbalance.fair_value_gap import FVGDetector
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class IFVGDetector(BaseSMCDetector):
    """A Fair Value Gap that later gets fully filled, inverting its expected reaction."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Inverse Fair Value Gap",
            category="Imbalance",
            description="A Fair Value Gap fully filled by later price action, inverting its expected reaction.",
            inputs=("High", "Low"),
            outputs=("ifvg",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        fvgs = FVGDetector().detect(context).detections
        data = context.data
        detections: list[SMCDetection] = []

        for fvg in fvgs:
            start = (fvg.end_index if fvg.end_index is not None else fvg.index) + 1
            fill_index = None
            for i in range(start, len(data)):
                if fvg.direction == "bullish" and float(data["Low"].iloc[i]) <= fvg.bottom:
                    fill_index = i
                    break
                if fvg.direction == "bearish" and float(data["High"].iloc[i]) >= fvg.top:
                    fill_index = i
                    break
            if fill_index is None:
                continue
            inverted_direction = "bearish" if fvg.direction == "bullish" else "bullish"
            detections.append(
                SMCDetection(
                    index=fill_index,
                    datetime=self._iso(context, fill_index),
                    label="Inverse FVG",
                    direction=inverted_direction,
                    top=fvg.top,
                    bottom=fvg.bottom,
                    notes=f"Originally a {fvg.direction} FVG at index {fvg.index}, fully filled.",
                )
            )
        return detections
