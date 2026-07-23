"""Dataset export (Phase 18.6) -- thin wrapper over
`app.data_engine.DataExporter`, never reimplementing it.
"""

from pathlib import Path
from typing import Literal

import pandas as pd

from app.data_engine.exporter import DataExporter

ExportFormat = Literal["csv", "parquet", "sqlite"]


class DatasetExporter:
    def __init__(self, exporter: DataExporter | None = None) -> None:
        self._exporter = exporter or DataExporter()

    def export(self, df: pd.DataFrame, target_path: str | Path, fmt: ExportFormat) -> Path:
        if fmt == "csv":
            return self._exporter.to_csv(df, target_path)
        if fmt == "parquet":
            return self._exporter.to_parquet(df, target_path)
        if fmt == "sqlite":
            return self._exporter.to_sqlite(df, target_path)
        raise ValueError(f"Unknown export format: {fmt!r}")
