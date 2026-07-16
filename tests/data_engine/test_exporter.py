"""Tests for DataExporter."""

import sqlite3

import pandas as pd

from app.data_engine.csv_importer import CSVImporter
from app.data_engine.exporter import DataExporter


def test_export_to_csv_roundtrip(valid_csv_path, tmp_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    out_path = tmp_path / "out.csv"
    DataExporter().to_csv(df, out_path)
    assert out_path.exists()
    reloaded = pd.read_csv(out_path)
    assert len(reloaded) == len(df)


def test_export_to_parquet_roundtrip(valid_csv_path, tmp_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    out_path = tmp_path / "out.parquet"
    DataExporter().to_parquet(df, out_path)
    assert out_path.exists()
    reloaded = pd.read_parquet(out_path)
    assert len(reloaded) == len(df)


def test_export_to_sqlite_roundtrip(valid_csv_path, tmp_path) -> None:
    df = CSVImporter().import_csv(valid_csv_path)
    out_path = tmp_path / "out.db"
    DataExporter().to_sqlite(df, out_path, table_name="candles")
    assert out_path.exists()
    with sqlite3.connect(out_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
    assert count == len(df)
