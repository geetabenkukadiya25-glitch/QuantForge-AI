"""The standardized, immutable output every detector produces.

Unlike `IndicatorResult` (a continuous value per candle), Smart Money
structures are discrete events and zones -- a swing high at one index, a
Fair Value Gap spanning a range of indices. `SMCResult` holds a tuple of
`SMCDetection`s rather than a value-per-candle series.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

SMC_RESULT_VERSION = "1.0.0"


@dataclass(frozen=True)
class SMCDetection:
    """A single detected structure: a point event or a price/time zone."""

    index: int
    datetime: str
    label: str
    direction: str | None = None
    price: float | None = None
    top: float | None = None
    bottom: float | None = None
    end_index: int | None = None
    end_datetime: str | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "datetime": self.datetime,
            "label": self.label,
            "direction": self.direction,
            "price": self.price,
            "top": self.top,
            "bottom": self.bottom,
            "end_index": self.end_index,
            "end_datetime": self.end_datetime,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SMCResult:
    """The computed output of a single detector run."""

    detector_name: str
    category: str
    detector_version: str
    result_version: str
    symbol: str | None
    timeframe: str | None
    parameters: dict[str, Any]
    detections: tuple[SMCDetection, ...] = field(default_factory=tuple)
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Return a plain, JSON-safe dict representation."""
        return {
            "detector_name": self.detector_name,
            "category": self.category,
            "detector_version": self.detector_version,
            "result_version": self.result_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "parameters": self.parameters,
            "detections": [d.to_dict() for d in self.detections],
            "computed_at": self.computed_at.isoformat(),
        }
