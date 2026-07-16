"""The standardized, immutable output every indicator produces.

`IndicatorResult` never stores a mutable pandas object directly -- output
series are stored as plain tuples, so the result is truly immutable
(unlike a DataFrame, which is always mutable in place) and trivially
serializable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

INDICATOR_RESULT_VERSION = "1.0.0"


@dataclass(frozen=True)
class IndicatorResult:
    """The computed output of a single indicator run."""

    indicator_name: str
    category: str
    indicator_version: str
    result_version: str
    symbol: str | None
    timeframe: str | None
    parameters: dict[str, Any]
    datetime_index: tuple[str, ...]
    values: dict[str, tuple[float | None, ...]]
    computed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for output_name, series in self.values.items():
            if len(series) != len(self.datetime_index):
                raise ValueError(
                    f"Output '{output_name}' has {len(series)} values but "
                    f"datetime_index has {len(self.datetime_index)} entries."
                )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain, JSON-safe dict representation."""
        return {
            "indicator_name": self.indicator_name,
            "category": self.category,
            "indicator_version": self.indicator_version,
            "result_version": self.result_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "parameters": self.parameters,
            "datetime_index": list(self.datetime_index),
            "values": {name: list(series) for name, series in self.values.items()},
            "computed_at": self.computed_at.isoformat(),
        }
