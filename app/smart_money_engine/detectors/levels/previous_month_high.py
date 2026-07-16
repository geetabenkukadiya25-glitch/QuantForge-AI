"""Previous Month High detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import previous_period_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PreviousMonthHighDetector(BaseSMCDetector):
    """The prior calendar month's highest High, referenced from the first candle of each new month."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Previous Month High",
            category="Levels",
            description="Prior calendar month's highest High, referenced at the start of each new month.",
            inputs=("High",),
            outputs=("previous_month_high",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        return [
            SMCDetection(index=index, datetime=self._iso(context, index), label="Previous Month High", price=price)
            for index, price in previous_period_extreme(context.data, "M", "High", "max")
        ]
