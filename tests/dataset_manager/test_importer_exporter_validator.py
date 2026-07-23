"""`app.dataset_manager.importer`/`exporter`/`validator` -- each wraps
`app.data_engine` without reimplementing it."""

from pathlib import Path

import pandas as pd
import pytest

from app.data_engine.exceptions import CSVFormatError
from app.dataset_manager.exporter import DatasetExporter
from app.dataset_manager.importer import DatasetImporter, hash_bytes
from app.dataset_manager.models import DatasetSource
from app.dataset_manager.validator import DatasetValidator


def test_hash_bytes_is_deterministic_sha256(valid_csv_bytes) -> None:
    assert hash_bytes(valid_csv_bytes) == hash_bytes(valid_csv_bytes)
    assert len(hash_bytes(valid_csv_bytes)) == 64


def test_import_from_bytes_builds_record_and_copies_file(tmp_path: Path, valid_csv_bytes) -> None:
    registry_dir = tmp_path / "registry"
    importer = DatasetImporter(registry_dir)
    record, df = importer.import_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv", source=DatasetSource.UPLOAD)

    assert record.filename == "EURUSD_H1.csv"
    assert record.rows == len(df)
    assert record.symbol == "EURUSD"
    assert record.timeframe == "H1"
    assert (registry_dir / f"{record.id}.csv").exists()
    assert record.hash == hash_bytes(valid_csv_bytes)


def test_import_from_bytes_rejects_malformed_csv(tmp_path: Path) -> None:
    importer = DatasetImporter(tmp_path / "registry")
    with pytest.raises(CSVFormatError):
        importer.import_from_bytes(b"not,a,valid\nheader\n", filename="bad.csv")


def test_load_dataframe_reads_back_registered_copy(tmp_path: Path, valid_csv_bytes) -> None:
    importer = DatasetImporter(tmp_path / "registry")
    record, original_df = importer.import_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    reloaded = importer.load_dataframe(record)
    assert len(reloaded) == len(original_df)


def test_exporter_writes_csv(tmp_path: Path) -> None:
    df = pd.DataFrame({"Open": [1.0, 1.1], "Close": [1.05, 1.15]})
    exporter = DatasetExporter()
    target = tmp_path / "out.csv"
    path = exporter.export(df, target, "csv")
    assert path.exists()
    assert pd.read_csv(path).shape == df.shape


def test_exporter_rejects_unknown_format(tmp_path: Path) -> None:
    df = pd.DataFrame({"Open": [1.0]})
    with pytest.raises(ValueError):
        DatasetExporter().export(df, tmp_path / "out.xyz", "xyz")


def test_validator_returns_result_and_health(tmp_path: Path, valid_csv_bytes) -> None:
    importer = DatasetImporter(tmp_path / "registry")
    record, df = importer.import_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    result, health = DatasetValidator().validate(df, timeframe=record.timeframe)
    assert result.total_candles == len(df)
    assert 0 <= health.score <= 100
