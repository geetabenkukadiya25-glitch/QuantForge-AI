"""Filesystem-backed storage for context snapshots.

Composes `ContextSerializer` rather than reimplementing serialization
(no duplicate business logic, per `PROJECT_VISION.md`).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.config.paths import get_paths
from app.context_engine.exceptions import ContextRegistryError
from app.context_engine.models import ContextSnapshot
from app.context_engine.serializer import ContextSerializer
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ContextSummary:
    """Lightweight metadata for listing registered snapshots."""

    snapshot_id: str
    symbol: str
    timeframe: str
    datetime_utc: str
    context_version: str
    file_path: Path


class ContextRegistry:
    """CRUD storage for `ContextSnapshot`s on disk."""

    def __init__(
        self,
        storage_dir: Path | None = None,
        serializer: ContextSerializer | None = None,
    ) -> None:
        self._dir = storage_dir or get_paths().context_snapshots_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._serializer = serializer or ContextSerializer()

    def save(self, snapshot: ContextSnapshot, overwrite: bool = False) -> Path:
        """Persist `snapshot` to the registry.

        Raises:
            ContextRegistryError: if a file for this snapshot id already
                exists and `overwrite` is False.
        """
        path = self._path_for(snapshot.snapshot_id)
        if path.exists() and not overwrite:
            raise ContextRegistryError(
                f"Snapshot '{snapshot.snapshot_id}' already exists at {path}. "
                "Pass overwrite=True to replace it."
            )
        path.write_text(self._serializer.to_json(snapshot), encoding="utf-8")
        logger.info("Saved context snapshot %s to %s", snapshot.snapshot_id, path)
        return path

    def load(self, snapshot_id: str) -> ContextSnapshot:
        """Load the snapshot with the given id.

        Raises:
            ContextRegistryError: if no file exists for `snapshot_id`.
        """
        path = self._path_for(snapshot_id)
        if not path.exists():
            raise ContextRegistryError(f"No snapshot found with id {snapshot_id!r} in {self._dir}")
        return self._serializer.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, snapshot_id: str) -> None:
        """Delete the stored snapshot with the given id.

        Raises:
            ContextRegistryError: if no file exists for `snapshot_id`.
        """
        path = self._path_for(snapshot_id)
        if not path.exists():
            raise ContextRegistryError(f"No snapshot found with id {snapshot_id!r} in {self._dir}")
        path.unlink()
        logger.info("Deleted context snapshot %s", snapshot_id)

    def list(self) -> list[ContextSummary]:
        """Return summaries for every snapshot in the registry."""
        summaries: list[ContextSummary] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                snapshot = self.load(path.stem)
            except Exception as exc:  # a corrupt file shouldn't break listing everything else
                logger.warning("Skipping unreadable context snapshot file %s: %s", path, exc)
                continue
            summaries.append(
                ContextSummary(
                    snapshot_id=snapshot.snapshot_id,
                    symbol=snapshot.market.symbol,
                    timeframe=snapshot.market.timeframe,
                    datetime_utc=snapshot.market.datetime_utc.isoformat(),
                    context_version=snapshot.context_version,
                    file_path=path,
                )
            )
        return summaries

    def _path_for(self, snapshot_id: str) -> Path:
        return self._dir / f"{snapshot_id}.json"
