"""Tests for generate_quality_report."""

from app.data_engine.csv_importer import CSVImporter
from app.data_engine.quality_report import generate_quality_report


def test_quality_report_on_valid_data(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    report = generate_quality_report(df)
    assert report.total_candles == 5
    assert report.duplicate_candles == 0
    assert report.invalid_candles == 0
    assert report.detected_timeframe == "H1"
    assert report.date_range_start is not None
    assert report.date_range_end is not None


def test_quality_report_on_duplicate_data(duplicate_csv_path) -> None:
    df = CSVImporter().import_csv(duplicate_csv_path)
    report = generate_quality_report(df)
    assert report.duplicate_candles == 1


def test_quality_report_to_dict_keys(valid_csv_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    report_dict = generate_quality_report(df).to_dict()
    assert set(report_dict.keys()) == {
        "total_candles",
        "date_range_start",
        "date_range_end",
        "detected_timeframe",
        "missing_candles",
        "duplicate_candles",
        "invalid_candles",
        "missing_values",
        "generated_at",
    }
