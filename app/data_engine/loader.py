"""Facade for loading, previewing, and summarizing historical OHLCV data.

`DataLoader` is the primary entrypoint for the historical data engine: it
composes `CSVImporter`, `DataCleaner`, `DataValidator`, and
`TimeframeConverter` into the load/preview/statistics workflow described
in the Phase 2 spec.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from app.data_engine.cleaner import DataCleaner
from app.data_engine.columns import DATETIME_COL
from app.data_engine.csv_importer import CSVImporter
from app.data_engine.timeframe_converter import TimeframeConverter
from app.data_engine.validator import DataValidator


class DataLoader:
    """Loads historical OHLCV data and exposes preview/statistics helpers."""

    def __init__(
        self,
        csv_importer: CSVImporter | None = None,
        cleaner: DataCleaner | None = None,
        validator: DataValidator | None = None,
        timeframe_converter: TimeframeConverter | None = None,
    ) -> None:
        self._csv_importer = csv_importer or CSVImporter()
        self._cleaner = cleaner or DataCleaner()
        self._validator = validator or DataValidator()
        self._timeframe_converter = timeframe_converter or TimeframeConverter()

    def load_csv(
        self,
        file_path: str | Path,
        clean: bool = True,
        tz: str | None = None,
    ) -> pd.DataFrame:
        """Load `file_path` into a standard-schema OHLCV DataFrame.

        Args:
            file_path: path to a CSV file (standard or MT5 export format).
            clean: if True (default), sort/dedupe/drop-NaT via `DataCleaner`.
            tz: optional IANA timezone to localize/convert timestamps to.
        """
        df = self._csv_importer.import_csv(file_path)
        if clean:
            df = self._cleaner.clean(df, tz=tz)
        return df

    def preview_head(self, df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        """Return the first `n` rows."""
        return df.head(n)

    def preview_tail(self, df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
        """Return the last `n` rows."""
        return df.tail(n)

    def statistics(self, df: pd.DataFrame) -> dict[str, Any]:
        """Return summary statistics: candle count, date range, missing/duplicate
        candles, detected timeframe, and memory usage (bytes).
        """
        detected_timeframe = self._timeframe_converter.detect_timeframe(df)
        validation = self._validator.validate(df, timeframe=detected_timeframe)
        timestamps = df[DATETIME_COL].dropna()

        return {
            "num_candles": len(df),
            "date_range_start": timestamps.min() if not timestamps.empty else None,
            "date_range_end": timestamps.max() if not timestamps.empty else None,
            "missing_candles": validation.missing_candles,
            "duplicate_candles": validation.duplicate_candles,
            "detected_timeframe": detected_timeframe,
            "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
        }
