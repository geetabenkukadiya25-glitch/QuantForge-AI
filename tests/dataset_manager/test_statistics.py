"""`app.dataset_manager.statistics`: pure `compute_statistics`."""

import pandas as pd

from app.data_engine.loader import DataLoader
from app.dataset_manager.statistics import compute_statistics


def test_compute_statistics_basic_fields(tmp_path, valid_csv_bytes) -> None:
    csv_path = tmp_path / "seed.csv"
    csv_path.write_bytes(valid_csv_bytes)
    loader = DataLoader()
    df = loader.load_csv(csv_path)
    loader_stats = loader.statistics(df)

    stats = compute_statistics(df, loader_stats, disk_size_bytes=len(valid_csv_bytes), symbol="EURUSD", timeframe="H1")

    assert stats.rows == len(df)
    assert stats.columns == len(df.columns)
    assert stats.candles == loader_stats["num_candles"]
    assert stats.symbol == "EURUSD"
    assert stats.timeframe == "H1"
    assert stats.sessions == 1  # all candles fall on the same calendar day
    assert stats.disk_size_bytes == len(valid_csv_bytes)
    assert stats.frequency == loader_stats["detected_timeframe"]
