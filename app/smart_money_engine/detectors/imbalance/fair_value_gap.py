"""Fair Value Gap (FVG) detector: the classic 3-candle wick-gap pattern."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class FVGDetector(BaseSMCDetector):
    """A 3-candle pattern where candle 1's wick doesn't overlap candle 3's wick."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Fair Value Gap",
            category="Imbalance",
            description="3-candle wick gap: candle 1's High/Low doesn't overlap candle 3's Low/High.",
            inputs=("High", "Low"),
            outputs=("fvg",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        data = context.data
        detections: list[SMCDetection] = []
        for i in range(2, len(data)):
            c1_high, c1_low = float(data["High"].iloc[i - 2]), float(data["Low"].iloc[i - 2])
            c3_high, c3_low = float(data["High"].iloc[i]), float(data["Low"].iloc[i])

            if c1_high < c3_low:
                detections.append(
                    SMCDetection(
                        index=i - 2,
                        datetime=self._iso(context, i - 2),
                        end_index=i,
                        end_datetime=self._iso(context, i),
                        label="Bullish FVG",
                        direction="bullish",
                        top=c3_low,
                        bottom=c1_high,
                    )
                )
            elif c1_low > c3_high:
                detections.append(
                    SMCDetection(
                        index=i - 2,
                        datetime=self._iso(context, i - 2),
                        end_index=i,
                        end_datetime=self._iso(context, i),
                        label="Bearish FVG",
                        direction="bearish",
                        top=c1_low,
                        bottom=c3_high,
                    )
                )
        return detections
