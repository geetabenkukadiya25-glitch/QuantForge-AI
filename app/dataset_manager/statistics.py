"""Pure function computing `DatasetStatistics` (Phase 18.6). Built on top
of `app.data_engine.DataLoader.statistics()` -- never recomputes what it
already provides (num_candles, date range, missing/duplicate candles,
detected timeframe, memory usage); only adds the handful of fields that
are dataset-*registry* concerns (disk size, symbol, sessions).
"""

from typing import Any

import pandas as pd

from app.data_engine.columns import DATETIME_COL
from app.dataset_manager.models import DatasetStatistics


def compute_statistics(
    df: pd.DataFrame,
    loader_stats: dict[str, Any],
    disk_size_bytes: int,
    symbol: str | None,
    timeframe: str | None,
) -> DatasetStatistics:
    sessions = 0
    if DATETIME_COL in df.columns:
        sessions = int(df[DATETIME_COL].dropna().dt.date.nunique())

    start = loader_stats.get("date_range_start")
    end = loader_stats.get("date_range_end")

    return DatasetStatistics(
        rows=len(df),
        columns=len(df.columns),
        candles=loader_stats.get("num_candles", len(df)),
        date_range_start=start.isoformat() if start is not None else None,
        date_range_end=end.isoformat() if end is not None else None,
        symbol=symbol,
        timeframe=timeframe,
        sessions=sessions,
        memory_usage_bytes=loader_stats.get("memory_usage_bytes", int(df.memory_usage(deep=True).sum())),
        disk_size_bytes=disk_size_bytes,
        frequency=loader_stats.get("detected_timeframe"),
    )
