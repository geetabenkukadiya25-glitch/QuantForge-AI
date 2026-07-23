"""Pure function computing a Dataset Health/Quality Score (Phase 18.6).

Never reimplements validation -- built entirely on top of an already
computed `app.data_engine.validator.ValidationResult` plus a handful of
extra checks (`DataValidator` doesn't cover negative prices, timezone,
sort order, or timeline continuity) using only pandas over the already
loaded DataFrame.
"""

import pandas as pd

from app.data_engine.columns import DATETIME_COL, OHLC_COLS, VOLUME_COL
from app.data_engine.validator import ValidationResult
from app.dataset_manager.models import DatasetHealth, HealthCheck

_DEDUCTIONS = {
    "missing_timestamps": 15,
    "duplicate_timestamps": 15,
    "missing_ohlc": 15,
    "negative_prices": 15,
    "invalid_high_low": 15,
    "invalid_volume": 5,
    "timezone": 5,
    "sorting": 10,
    "continuity": 5,
}


def compute_health(df: pd.DataFrame, validation: ValidationResult) -> DatasetHealth:
    checks: list[HealthCheck] = []
    warnings: list[str] = []
    errors: list[str] = []
    suggestions: list[str] = []
    score = 100

    def _check(name: str, passed: bool, ok_message: str, fail_message: str, *, is_error: bool = False) -> None:
        nonlocal score
        checks.append(HealthCheck(name=name, passed=passed, message=ok_message if passed else fail_message))
        if not passed:
            score -= _DEDUCTIONS[name]
            (errors if is_error else warnings).append(fail_message)

    _check(
        "missing_timestamps",
        validation.invalid_timestamps == 0,
        "No unparseable timestamps.",
        f"{validation.invalid_timestamps} row(s) with unparseable timestamps.",
        is_error=True,
    )
    _check(
        "duplicate_timestamps",
        validation.duplicate_candles == 0,
        "No duplicate candles.",
        f"{validation.duplicate_candles} duplicate candle(s).",
        is_error=True,
    )
    missing_ohlc = sum(validation.missing_values.get(col, 0) for col in OHLC_COLS)
    _check(
        "missing_ohlc",
        missing_ohlc == 0,
        "No missing OHLC values.",
        f"{missing_ohlc} missing OHLC value(s).",
        is_error=True,
    )

    negative_prices = 0
    if all(col in df.columns for col in OHLC_COLS):
        negative_prices = int((df[OHLC_COLS] < 0).any(axis=1).sum())
    _check(
        "negative_prices",
        negative_prices == 0,
        "No negative prices.",
        f"{negative_prices} candle(s) with a negative price.",
        is_error=True,
    )

    _check(
        "invalid_high_low",
        validation.invalid_ohlc_candles == 0,
        "High/Low/Open/Close are internally consistent.",
        f"{validation.invalid_ohlc_candles} candle(s) with inconsistent High/Low/Open/Close.",
        is_error=True,
    )

    invalid_volume = 0
    if VOLUME_COL in df.columns:
        invalid_volume = int((df[VOLUME_COL] < 0).sum())
    _check(
        "invalid_volume",
        invalid_volume == 0,
        "No negative volume.",
        f"{invalid_volume} candle(s) with negative volume.",
    )

    has_tz = DATETIME_COL in df.columns and getattr(df[DATETIME_COL].dt, "tz", None) is not None
    _check(
        "timezone",
        has_tz,
        "Datetime column is timezone-aware.",
        "Datetime column has no timezone information.",
    )
    if not has_tz:
        suggestions.append("Consider localizing the Datetime column to a timezone before cross-dataset comparisons.")

    is_sorted = DATETIME_COL in df.columns and bool(df[DATETIME_COL].is_monotonic_increasing)
    _check(
        "sorting",
        is_sorted,
        "Candles are sorted by Datetime.",
        "Candles are not sorted in ascending Datetime order.",
    )
    if not is_sorted:
        suggestions.append("Reindex this dataset to sort candles by Datetime.")

    _check(
        "continuity",
        validation.missing_candles == 0,
        "No gaps detected in the timeline.",
        f"~{validation.missing_candles} missing candle(s) in the timeline.",
    )
    if validation.missing_candles:
        suggestions.append("Reindex or re-import this dataset to fill timeline gaps.")

    return DatasetHealth(
        score=max(0, score),
        checks=tuple(checks),
        warnings=tuple(warnings),
        errors=tuple(errors),
        suggestions=tuple(suggestions),
    )
