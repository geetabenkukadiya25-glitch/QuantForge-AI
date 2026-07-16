"""Tests for TimeframeConverter."""

from app.data_engine.csv_importer import CSVImporter
from app.data_engine.timeframe_converter import TimeframeConverter


def test_detect_timeframe_hourly(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    assert TimeframeConverter().detect_timeframe(df) == "H1"


def test_resample_to_larger_timeframe(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    resampled = TimeframeConverter().resample(df, "H4")
    assert len(resampled) < len(df)
    assert resampled["Open"].iloc[0] == df["Open"].iloc[0]
    assert resampled["High"].iloc[0] == df["High"].iloc[:4].max()
