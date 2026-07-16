"""Previous Day Low detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import previous_period_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PreviousDayLowDetector(BaseSMCDetector):
    """The prior calendar day's lowest Low, referenced from the first candle of each new day."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Previous Day Low",
            category="Levels",
            description="Prior calendar day's lowest Low, referenced at the start of each new day.",
            inputs=("Low",),
            outputs=("previous_day_low",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        return [
            SMCDetection(index=index, datetime=self._iso(context, index), label="Previous Day Low", price=price)
            for index, price in previous_period_extreme(context.data, "D", "Low", "min")
        ]
