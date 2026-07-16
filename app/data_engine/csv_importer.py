"""CSV import for historical OHLCV data.

Supports standard CSV exports (`Date, Time, Open, High, Low, Close,
Tick Volume, Volume, Spread`) as well as raw MetaTrader 5 terminal
exports (tab-separated, `<DATE> <TIME> <OPEN> ...` headers). `Date` and
`Time` columns are automatically merged into a single `Datetime` column.
"""

from pathlib import Path

import pandas as pd

from app.data_engine.columns import (
    DATETIME_COL,
    OHLC_COLS,
    SPREAD_COL,
    STANDARD_COLUMNS,
    VOLUME_COL,
    resolve_header_aliases,
)
from app.data_engine.exceptions import CSVFormatError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CSVImporter:
    """Parses a CSV file into a standard-schema OHLCV DataFrame."""

    def import_csv(self, file_path: str | Path) -> pd.DataFrame:
        """Read `file_path` and return a DataFrame with `STANDARD_COLUMNS`.

        Raises:
            CSVFormatError: if the file is missing, empty, or lacks the
                columns required to build a valid OHLCV table.
        """
        path = Path(file_path)
        if not path.exists():
            raise CSVFormatError(f"CSV file not found: {path}")

        try:
            raw = pd.read_csv(path, sep=None, engine="python")
        except Exception as exc:  # pandas raises various error types
            raise CSVFormatError(f"Could not parse CSV file '{path}': {exc}") from exc

        if raw.empty:
            raise CSVFormatError(f"CSV file is empty: {path}")

        return self._normalize(raw, source=str(path))

    def import_dataframe(self, raw: pd.DataFrame, source: str = "<dataframe>") -> pd.DataFrame:
        """Normalize an already-loaded raw DataFrame (e.g. from an upload widget)."""
        return self._normalize(raw, source=source)

    def _normalize(self, raw: pd.DataFrame, source: str) -> pd.DataFrame:
        alias_map = resolve_header_aliases(list(raw.columns))
        df = raw.rename(columns=alias_map)

        missing_ohlc = [col for col in OHLC_COLS if col not in df.columns]
        if missing_ohlc:
            raise CSVFormatError(
                f"'{source}' is missing required OHLC column(s): {missing_ohlc}"
            )

        df[DATETIME_COL] = self._build_datetime_column(df, source)

        if VOLUME_COL not in df.columns:
            if "TickVolume" in df.columns:
                df[VOLUME_COL] = df["TickVolume"]
            else:
                df[VOLUME_COL] = 0

        if SPREAD_COL not in df.columns:
            df[SPREAD_COL] = 0

        for col in OHLC_COLS + [VOLUME_COL, SPREAD_COL]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        result = df[STANDARD_COLUMNS].copy()
        logger.info("Imported %d rows from '%s'", len(result), source)
        return result

    @staticmethod
    def _build_datetime_column(df: pd.DataFrame, source: str) -> pd.Series:
        if DATETIME_COL in df.columns:
            return pd.to_datetime(df[DATETIME_COL], errors="coerce")

        if "Date" in df.columns and "Time" in df.columns:
            combined = (
                df["Date"].astype(str).str.strip() + " " + df["Time"].astype(str).str.strip()
            )
            return pd.to_datetime(combined, errors="coerce")

        if "Date" in df.columns:
            return pd.to_datetime(df["Date"], errors="coerce")

        raise CSVFormatError(
            f"'{source}' has no 'Datetime' column and no 'Date'/'Time' columns to merge."
        )
