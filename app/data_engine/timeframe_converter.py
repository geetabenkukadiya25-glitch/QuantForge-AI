"""Timeframe detection and resampling for historical OHLCV data."""

import pandas as pd

from app.data_engine.columns import DATETIME_COL, TIMEFRAME_TO_PANDAS_FREQ
from app.data_engine.exceptions import DataEngineError
from app.data_engine.freq_utils import freq_to_timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TimeframeConverter:
    """Detects a dataset's timeframe and resamples between timeframes."""

    def detect_timeframe(self, df: pd.DataFrame) -> str | None:
        """Return the standard timeframe label (e.g. "H1") whose spacing best
        matches the modal gap between consecutive candles, or None if the
        dataset has fewer than two rows.
        """
        timestamps = df[DATETIME_COL].dropna().sort_values()
        if len(timestamps) < 2:
            return None

        modal_gap = timestamps.diff().dropna().mode()
        if modal_gap.empty:
            return None
        gap = modal_gap.iloc[0]

        closest_label = min(
            TIMEFRAME_TO_PANDAS_FREQ,
            key=lambda label: abs(freq_to_timedelta(TIMEFRAME_TO_PANDAS_FREQ[label]) - gap),
        )
        return closest_label

    def resample(self, df: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
        """Resample `df` (standard schema) to `target_timeframe` (e.g. "H4").

        Raises:
            DataEngineError: if `target_timeframe` is not a recognized label.
        """
        freq = TIMEFRAME_TO_PANDAS_FREQ.get(target_timeframe)
        if freq is None:
            raise DataEngineError(f"Unknown timeframe label: {target_timeframe!r}")

        indexed = df.set_index(DATETIME_COL).sort_index()
        resampled = indexed.resample(freq).agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
                "Spread": "mean",
            }
        )
        resampled = resampled.dropna(subset=["Open", "High", "Low", "Close"])
        result = resampled.reset_index()
        logger.info(
            "Resampled %d candles to %s -> %d candles", len(df), target_timeframe, len(result)
        )
        return result
