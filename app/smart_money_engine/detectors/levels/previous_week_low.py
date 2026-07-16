"""Previous Week Low detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import previous_period_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PreviousWeekLowDetector(BaseSMCDetector):
    """The prior ISO week's lowest Low, referenced from the first candle of each new week."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Previous Week Low",
            category="Levels",
            description="Prior ISO week's lowest Low, referenced at the start of each new week.",
            inputs=("Low",),
            outputs=("previous_week_low",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        return [
            SMCDetection(index=index, datetime=self._iso(context, index), label="Previous Week Low", price=price)
            for index, price in previous_period_extreme(context.data, "W", "Low", "min")
        ]
