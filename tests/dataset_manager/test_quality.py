"""`app.dataset_manager.quality`: health/quality score computation."""

import pandas as pd

from app.data_engine.validator import DataValidator
from app.dataset_manager.quality import compute_health


def _df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    return df


def test_clean_sorted_data_scores_high() -> None:
    df = _df(
        [
            {"Datetime": "2024-01-01 00:00", "Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15, "Volume": 10},
            {"Datetime": "2024-01-01 01:00", "Open": 1.15, "High": 1.25, "Low": 1.05, "Close": 1.2, "Volume": 12},
        ]
    )
    validation = DataValidator().validate(df, timeframe="H1")
    health = compute_health(df, validation)
    assert health.score >= 80
    assert not health.errors


def test_negative_prices_and_invalid_high_low_are_flagged() -> None:
    df = _df(
        [
            {"Datetime": "2024-01-01 00:00", "Open": -1.1, "High": 1.0, "Low": 1.2, "Close": 1.15, "Volume": 10},
        ]
    )
    validation = DataValidator().validate(df, timeframe="H1")
    health = compute_health(df, validation)
    check_names = {c.name for c in health.checks if not c.passed}
    assert "negative_prices" in check_names
    assert "invalid_high_low" in check_names
    assert health.score < 100


def test_duplicate_timestamps_flagged() -> None:
    df = _df(
        [
            {"Datetime": "2024-01-01 00:00", "Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15, "Volume": 10},
            {"Datetime": "2024-01-01 00:00", "Open": 1.1, "High": 1.2, "Low": 1.0, "Close": 1.15, "Volume": 10},
        ]
    )
    validation = DataValidator().validate(df, timeframe="H1")
    health = compute_health(df, validation)
    assert any(c.name == "duplicate_timestamps" and not c.passed for c in health.checks)
