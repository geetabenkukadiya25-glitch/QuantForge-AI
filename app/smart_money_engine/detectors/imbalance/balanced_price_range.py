"""Balanced Price Range (BPR) detector: overlapping opposite-direction FVGs."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.imbalance.fair_value_gap import FVGDetector
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class BPRDetector(BaseSMCDetector):
    """A bullish and a bearish Fair Value Gap whose price zones overlap."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Balanced Price Range",
            category="Imbalance",
            description="A bullish and a bearish Fair Value Gap whose price zones overlap.",
            inputs=("High", "Low"),
            outputs=("bpr",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        fvgs = sorted(FVGDetector().detect(context).detections, key=lambda d: d.index)
        detections: list[SMCDetection] = []

        for a, b in zip(fvgs, fvgs[1:]):
            if a.direction == b.direction:
                continue
            top = min(a.top, b.top)
            bottom = max(a.bottom, b.bottom)
            if top <= bottom:
                continue
            detections.append(
                SMCDetection(
                    index=a.index,
                    datetime=a.datetime,
                    end_index=b.end_index,
                    end_datetime=b.end_datetime,
                    label="Balanced Price Range",
                    top=top,
                    bottom=bottom,
                    notes=f"Overlap of a {a.direction} FVG and a {b.direction} FVG.",
                )
            )
        return detections
