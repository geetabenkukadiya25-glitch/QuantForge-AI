"""Impulse Move detector: consecutive same-direction displacement candles."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.momentum.displacement import DisplacementDetector
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class ImpulseMoveDetector(BaseSMCDetector):
    """A run of one or more consecutive displacement candles in the same direction."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Impulse Move",
            category="Momentum",
            description="A run of one or more consecutive displacement candles in the same direction.",
            inputs=("Open", "High", "Low", "Close"),
            outputs=("impulse_move",),
            parameters=(
                ParameterSpec("window", "int", default=14, minimum=1),
                ParameterSpec("multiplier", "float", default=2.0, minimum=0.0),
                ParameterSpec("min_candles", "int", default=2, minimum=1),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        displacements = DisplacementDetector(
            window=self.params["window"], multiplier=self.params["multiplier"]
        ).detect(context).detections
        min_candles = self.params["min_candles"]
        data = context.data

        detections: list[SMCDetection] = []
        group: list = []
        for detection in displacements:
            if group and (
                detection.direction != group[-1].direction or detection.index != group[-1].index + 1
            ):
                if len(group) >= min_candles:
                    detections.append(self._build(context, group))
                group = []
            group.append(detection)
        if len(group) >= min_candles:
            detections.append(self._build(context, group))
        return detections

    def _build(self, context: SMCContext, group: list) -> SMCDetection:
        data = context.data
        start, end = group[0].index, group[-1].index
        direction = group[0].direction
        if direction == "bullish":
            top, bottom = float(data["High"].iloc[start : end + 1].max()), float(data["Low"].iloc[start])
        else:
            top, bottom = float(data["High"].iloc[start]), float(data["Low"].iloc[start : end + 1].min())
        return SMCDetection(
            index=start,
            datetime=self._iso(context, start),
            end_index=end,
            end_datetime=self._iso(context, end),
            label="Bullish Impulse Move" if direction == "bullish" else "Bearish Impulse Move",
            direction=direction,
            top=top,
            bottom=bottom,
            notes=f"{len(group)} consecutive displacement candle(s).",
        )
