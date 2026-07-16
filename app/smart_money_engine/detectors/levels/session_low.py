"""Session Low detector: the lowest price within each trading session."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.levels._session_groups import session_extreme
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMCDetection


class SessionLowDetector(BaseSMCDetector):
    """The lowest Low within each (day, trading session) group."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Session Low",
            category="Levels",
            description="Lowest Low within each (day, trading session) group (Sydney/Tokyo/London/New York).",
            inputs=("Low",),
            outputs=("session_low",),
            parameters=(),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        extremes = session_extreme(context.data, "Low", "min")
        return [
            SMCDetection(
                index=index,
                datetime=self._iso(context, index),
                end_index=end,
                end_datetime=self._iso(context, end),
                label="Session Low",
                price=price,
                notes=f"{session_name} session.",
            )
            for index, price, session_name, start, end in extremes
        ]
