"""Previous Day High detector."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import previous_period_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class PreviousDayHighDetector(BaseSMCDetector):
    """The prior calendar day's highest High, referenced from the first candle of each new day."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Previous Day High",
            category="Levels",
            description="Prior calendar day's highest High, referenced at the start of each new day.",
            inputs=("High",),
            outputs=("previous_day_high",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        return [
            SMCDetection(index=index, datetime=self._iso(context, index), label="Previous Day High", price=price)
            for index, price in previous_period_extreme(context.data, "D", "High", "max")
        ]
