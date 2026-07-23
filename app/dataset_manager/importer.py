"""Dataset import (Phase 18.6) -- wraps `app.data_engine.DataLoader` (and
therefore `CSVImporter`/`DataCleaner`/`DataValidator`/`TimeframeConverter`)
and `app.ui.dataset_detection`, never reimplementing any of them. Adds
only what's unique to *registry* management: content hashing for dedup,
copying the raw file into the managed registry directory, and building
the initial `DatasetRecord`.
"""

import hashlib
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.data_engine.loader import DataLoader
from app.data_engine.validator import DataValidator
from app.dataset_manager.models import DatasetRecord, DatasetSource
from app.ui.dataset_detection import detect_symbol_from_filename, detect_timeframe_from_datetime, detect_timeframe_from_filename


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DatasetImporter:
    """Produces a `(DatasetRecord, DataFrame)` pair from raw CSV bytes,
    plus a copy of the raw file at `registry_dir / f"{id}.csv"`. Never
    registers into any store itself -- `DatasetManager` owns dedup/persist."""

    def __init__(self, registry_dir: Path, loader: DataLoader | None = None) -> None:
        self._registry_dir = registry_dir
        self._loader = loader or DataLoader()

    def import_from_bytes(
        self,
        data: bytes,
        filename: str,
        display_name: str | None = None,
        tags: tuple[str, ...] = (),
        description: str = "",
        notes: str = "",
        dataset_id: str | None = None,
        source: DatasetSource = DatasetSource.UPLOAD,
        clean: bool = True,
    ) -> tuple[DatasetRecord, pd.DataFrame]:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(data)
            tmp_path = Path(tmp.name)
        try:
            df = self._loader.load_csv(tmp_path, clean=clean)
        finally:
            tmp_path.unlink(missing_ok=True)

        loader_stats = self._loader.statistics(df)
        symbol = detect_symbol_from_filename(filename)
        timeframe = detect_timeframe_from_filename(filename) or detect_timeframe_from_datetime(df) or loader_stats.get("detected_timeframe")
        validation = DataValidator().validate(df, timeframe=timeframe)

        record_id = dataset_id or uuid.uuid4().hex
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._registry_dir / f"{record_id}.csv"
        target_path.write_bytes(data)

        content_hash = hash_bytes(data)
        now = datetime.now(timezone.utc)
        record = DatasetRecord(
            id=record_id,
            filename=filename,
            display_name=display_name or filename,
            import_date=now,
            created=now,
            modified=now,
            file_size=len(data),
            rows=len(df),
            columns=len(df.columns),
            candles=loader_stats.get("num_candles", len(df)),
            symbol=symbol,
            timeframe=timeframe,
            hash=content_hash,
            source=source,
            checksum=content_hash[:12],
            missing_values=sum(validation.missing_values.values()),
            duplicate_rows=validation.duplicate_candles,
            tags=list(tags),
            description=description,
            notes=notes,
        )
        return record, df

    def load_dataframe(self, record: DatasetRecord) -> pd.DataFrame:
        path = self._registry_dir / f"{record.id}.csv"
        return self._loader.load_csv(path, clean=False)
