"""Cleaning routines for historical OHLCV data.

Sorts by timestamp, drops unparseable/duplicate candles, and optionally
applies timezone localization/conversion. Never mutates the input
DataFrame in place.
"""

import pandas as pd

from app.data_engine.columns import DATETIME_COL
from app.data_engine.validator import DataValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataCleaner:
    """Produces a sorted, de-duplicated, timezone-consistent OHLCV DataFrame."""

    def clean(
        self,
        df: pd.DataFrame,
        tz: str | None = None,
        drop_invalid_ohlc: bool = False,
    ) -> pd.DataFrame:
        """Return a cleaned copy of `df`.

        Args:
            df: a standard-schema OHLCV DataFrame.
            tz: IANA timezone name. Naive timestamps are localized to it;
                aware timestamps are converted to it. `None` leaves
                timestamps untouched.
            drop_invalid_ohlc: if True, also drops candles that fail
                High >= Low / Open,Close-inside-range checks.
        """
        cleaned = df.copy()
        before = len(cleaned)

        cleaned = cleaned.dropna(subset=[DATETIME_COL])
        cleaned = cleaned.sort_values(DATETIME_COL)
        cleaned = cleaned.drop_duplicates(subset=[DATETIME_COL], keep="first")

        if drop_invalid_ohlc:
            invalid_mask = DataValidator.invalid_ohlc_mask(cleaned)
            cleaned = cleaned.loc[~invalid_mask]

        if tz is not None:
            cleaned[DATETIME_COL] = self._apply_timezone(cleaned[DATETIME_COL], tz)

        cleaned = cleaned.reset_index(drop=True)
        logger.info(
            "Cleaned data: %d -> %d rows (%d removed)", before, len(cleaned), before - len(cleaned)
        )
        return cleaned

    @staticmethod
    def _apply_timezone(series: pd.Series, tz: str) -> pd.Series:
        if series.dt.tz is None:
            return series.dt.tz_localize(tz)
        return series.dt.tz_convert(tz)
