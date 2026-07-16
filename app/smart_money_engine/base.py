"""Abstract base class every Smart Money detector implements.

A detector is a pure structural-analysis component: given an
`SMCContext` (OHLCV data), it returns an `SMCResult` describing what it
found. It never generates buy/sell signals, never contains strategy
logic, and never executes trades -- interpretation of detected
structures is a future engine's job.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.result import SMC_RESULT_VERSION, SMCDetection, SMCResult
from app.smart_money_engine.schema import DATETIME_COL


class BaseSMCDetector(ABC):
    """Common contract every Smart Money detector implementation satisfies."""

    def __init__(self, **params: Any) -> None:
        metadata = self.metadata()
        self.params: dict[str, Any] = {**metadata.default_params(), **params}

    @classmethod
    @abstractmethod
    def metadata(cls) -> SMCMetadata:
        """Return this detector's static description (name, category, inputs,
        outputs, parameters, version)."""

    @abstractmethod
    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        """Run the detection logic and return raw `SMCDetection`s.

        Subclasses implement only this; `detect()` wraps the result into
        a standardized `SMCResult`.
        """

    def detect(self, context: SMCContext) -> SMCResult:
        """Run the detector over `context` and return an `SMCResult`."""
        metadata = self.metadata()
        detections = self._detect(context)

        return SMCResult(
            detector_name=metadata.name,
            category=metadata.category,
            detector_version=metadata.version,
            result_version=SMC_RESULT_VERSION,
            symbol=context.symbol,
            timeframe=context.timeframe,
            parameters=dict(self.params),
            detections=tuple(detections),
        )

    @staticmethod
    def _iso(context: SMCContext, index: int) -> str:
        """ISO-format the `Datetime` value at `index`."""
        value = context.data[DATETIME_COL].iloc[index]
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
