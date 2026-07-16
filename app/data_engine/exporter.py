"""Export historical OHLCV data to CSV, Parquet, or SQLite."""

import sqlite3
from pathlib import Path

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """Writes a standard-schema OHLCV DataFrame to a target file/table."""

    def to_csv(self, df: pd.DataFrame, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        logger.info("Exported %d rows to CSV: %s", len(df), path)
        return path

    def to_parquet(self, df: pd.DataFrame, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        logger.info("Exported %d rows to Parquet: %s", len(df), path)
        return path

    def to_sqlite(
        self,
        df: pd.DataFrame,
        db_path: str | Path,
        table_name: str = "historical_data",
        if_exists: str = "replace",
    ) -> Path:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as conn:
            df.to_sql(table_name, conn, if_exists=if_exists, index=False)
        logger.info("Exported %d rows to SQLite: %s (table=%s)", len(df), path, table_name)
        return path
