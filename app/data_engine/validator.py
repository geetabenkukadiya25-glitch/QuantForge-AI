"""Validation checks for historical OHLCV data.

Checks missing candles, duplicate candles, invalid timestamps, and OHLC
consistency (High >= Low, Open/Close inside the [Low, High] range)
without mutating the input DataFrame.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.data_engine.columns import DATETIME_COL, OHLC_COLS, TIMEFRAME_TO_PANDAS_FREQ
from app.data_engine.exceptions import DataValidationError
from app.data_engine.freq_utils import freq_to_timedelta
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Outcome of running `DataValidator.validate` on a DataFrame."""

    total_candles: int
    invalid_timestamps: int
    duplicate_candles: int
    missing_candles: int
    invalid_ohlc_candles: int
    missing_values: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True when no structural problems were found."""
        return (
            self.invalid_timestamps == 0
            and self.duplicate_candles == 0
            and self.invalid_ohlc_candles == 0
            and not any(count > 0 for count in self.missing_values.values())
        )


class DataValidator:
    """Runs structural and OHLC-consistency checks over a historical dataset."""

    def validate(
        self, df: pd.DataFrame, timeframe: str | None = None
    ) -> ValidationResult:
        """Validate `df` and return a `ValidationResult`.

        Args:
            df: a standard-schema OHLCV DataFrame (see `columns.STANDARD_COLUMNS`).
            timeframe: expected timeframe label (e.g. "H1") used to estimate
                missing candles. If omitted, the modal spacing of `df` is used.

        Raises:
            DataValidationError: if `df` lacks the columns required to validate.
        """
        required = [DATETIME_COL, *OHLC_COLS]
        missing_cols = [col for col in required if col not in df.columns]
        if missing_cols:
            raise DataValidationError(f"Cannot validate: missing column(s) {missing_cols}")

        issues: list[str] = []

        invalid_timestamps = int(df[DATETIME_COL].isna().sum())
        if invalid_timestamps:
            issues.append(f"{invalid_timestamps} row(s) with unparseable timestamps")

        duplicate_candles = int(df[DATETIME_COL].duplicated().sum())
        if duplicate_candles:
            issues.append(f"{duplicate_candles} duplicate candle(s)")

        invalid_ohlc_mask = self.invalid_ohlc_mask(df)
        invalid_ohlc_candles = int(invalid_ohlc_mask.sum())
        if invalid_ohlc_candles:
            issues.append(f"{invalid_ohlc_candles} candle(s) with inconsistent OHLC values")

        missing_values = {col: int(df[col].isna().sum()) for col in required}
        for col, count in missing_values.items():
            if count:
                issues.append(f"{count} missing value(s) in '{col}'")

        missing_candles = self._estimate_missing_candles(df, timeframe)
        if missing_candles:
            issues.append(f"~{missing_candles} missing candle(s) in the timeline")

        result = ValidationResult(
            total_candles=len(df),
            invalid_timestamps=invalid_timestamps,
            duplicate_candles=duplicate_candles,
            missing_candles=missing_candles,
            invalid_ohlc_candles=invalid_ohlc_candles,
            missing_values=missing_values,
            issues=issues,
        )
        logger.info(
            "Validated %d candles: valid=%s, issues=%d",
            result.total_candles,
            result.is_valid,
            len(issues),
        )
        return result

    @staticmethod
    def invalid_ohlc_mask(df: pd.DataFrame) -> pd.Series:
        """Boolean mask of rows failing High >= Low / Open,Close-inside-range checks."""
        high, low, open_, close = df["High"], df["Low"], df["Open"], df["Close"]
        return (
            (high < low)
            | (open_ > high)
            | (open_ < low)
            | (close > high)
            | (close < low)
        ).fillna(False)

    @staticmethod
    def _estimate_missing_candles(df: pd.DataFrame, timeframe: str | None) -> int:
        timestamps = df[DATETIME_COL].dropna().sort_values()
        if len(timestamps) < 2:
            return 0

        if timeframe is not None:
            freq = TIMEFRAME_TO_PANDAS_FREQ.get(timeframe)
            if freq is None:
                raise DataValidationError(f"Unknown timeframe label: {timeframe!r}")
            step = freq_to_timedelta(freq)
        else:
            step = timestamps.diff().dropna().mode()
            if step.empty:
                return 0
            step = step.iloc[0]

        if step <= pd.Timedelta(0):
            return 0

        span = timestamps.iloc[-1] - timestamps.iloc[0]
        expected_candles = int(span / step) + 1
        return max(expected_candles - len(timestamps), 0)
