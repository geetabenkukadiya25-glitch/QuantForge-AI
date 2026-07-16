"""Previous Month Low detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import previous_period_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PreviousMonthLowDetector(BaseSMCDetector):
    """The prior calendar month's lowest Low, referenced from the first candle of each new month."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Previous Month Low",
            category="Levels",
            description="Prior calendar month's lowest Low, referenced at the start of each new month.",
            inputs=("Low",),
            outputs=("previous_month_low",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        return [
            SMCDetection(index=index, datetime=self._iso(context, index), label="Previous Month Low", price=price)
            for index, price in previous_period_extreme(context.data, "M", "Low", "min")
        ]
