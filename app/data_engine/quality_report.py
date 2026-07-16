"""Data quality report generation for historical OHLCV datasets."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.data_engine.columns import DATETIME_COL
from app.data_engine.timeframe_converter import TimeframeConverter
from app.data_engine.validator import DataValidator


@dataclass
class DataQualityReport:
    """Summary of a historical dataset's completeness and correctness."""

    total_candles: int
    date_range_start: pd.Timestamp | None
    date_range_end: pd.Timestamp | None
    detected_timeframe: str | None
    missing_candles: int
    duplicate_candles: int
    invalid_candles: int
    missing_values: dict[str, int] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_candles": self.total_candles,
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "detected_timeframe": self.detected_timeframe,
            "missing_candles": self.missing_candles,
            "duplicate_candles": self.duplicate_candles,
            "invalid_candles": self.invalid_candles,
            "missing_values": self.missing_values,
            "generated_at": self.generated_at,
        }


def generate_quality_report(
    df: pd.DataFrame,
    validator: DataValidator | None = None,
    timeframe_converter: TimeframeConverter | None = None,
) -> DataQualityReport:
    """Build a `DataQualityReport` for `df` (standard-schema OHLCV data)."""
    validator = validator or DataValidator()
    timeframe_converter = timeframe_converter or TimeframeConverter()

    detected_timeframe = timeframe_converter.detect_timeframe(df)
    validation = validator.validate(df, timeframe=detected_timeframe)

    timestamps = df[DATETIME_COL].dropna()
    date_range_start = timestamps.min() if not timestamps.empty else None
    date_range_end = timestamps.max() if not timestamps.empty else None

    return DataQualityReport(
        total_candles=validation.total_candles,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        detected_timeframe=detected_timeframe,
        missing_candles=validation.missing_candles,
        duplicate_candles=validation.duplicate_candles,
        invalid_candles=validation.invalid_ohlc_candles,
        missing_values=validation.missing_values,
    )
