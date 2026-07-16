"""Volume Imbalance detector: a gap between consecutive candle bodies (not wicks)."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class VolumeImbalanceDetector(BaseSMCDetector):
    """A 2-candle pattern where consecutive candle *bodies* (Open/Close) don't overlap."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Volume Imbalance",
            category="Imbalance",
            description="A gap between consecutive candle bodies (Open/Close), distinct from a wick-based FVG.",
            inputs=("Open", "Close"),
            outputs=("volume_imbalance",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        data = context.data
        detections: list[SMCDetection] = []
        for i in range(1, len(data)):
            open_prev, close_prev = float(data["Open"].iloc[i - 1]), float(data["Close"].iloc[i - 1])
            open_cur, close_cur = float(data["Open"].iloc[i]), float(data["Close"].iloc[i])
            body_prev_top, body_prev_bottom = max(open_prev, close_prev), min(open_prev, close_prev)
            body_cur_top, body_cur_bottom = max(open_cur, close_cur), min(open_cur, close_cur)

            if body_prev_top < body_cur_bottom:
                detections.append(
                    self._build(context, i - 1, i, "Bullish Volume Imbalance", "bullish", body_cur_bottom, body_prev_top)
                )
            elif body_cur_top < body_prev_bottom:
                detections.append(
                    self._build(context, i - 1, i, "Bearish Volume Imbalance", "bearish", body_prev_bottom, body_cur_top)
                )
        return detections

    def _build(self, context, start, end, label, direction, top, bottom) -> SMCDetection:
        return SMCDetection(
            index=start,
            datetime=self._iso(context, start),
            end_index=end,
            end_datetime=self._iso(context, end),
            label=label,
            direction=direction,
            top=top,
            bottom=bottom,
        )
