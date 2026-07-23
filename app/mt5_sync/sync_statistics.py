"""Synchronization statistics (Phase 19.2) -- small persisted counters,
mirroring the `MT5ManagerState`/`BridgeExchangeState` persisted-counters
idiom already used twice in `app/mt5/`.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.mt5_sync.sync_models import SyncRun, SyncStatus


@dataclass
class SyncStatistics:
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    runs_by_kind: dict[str, int] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    last_run_at: datetime | None = None

    @property
    def average_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_runs if self.total_runs else 0.0

    def record(self, run: SyncRun) -> None:
        self.total_runs += 1
        if run.status == SyncStatus.COMPLETED:
            self.success_count += 1
        elif run.status == SyncStatus.FAILED:
            self.failure_count += 1
        self.runs_by_kind[run.kind.value] = self.runs_by_kind.get(run.kind.value, 0) + 1
        if run.latency_ms is not None:
            self.total_latency_ms += run.latency_ms
        self.last_run_at = run.completed_at or run.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "runs_by_kind": dict(self.runs_by_kind),
            "total_latency_ms": self.total_latency_ms,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SyncStatistics":
        last_run_at = data.get("last_run_at")
        return SyncStatistics(
            total_runs=data.get("total_runs", 0),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            runs_by_kind=dict(data.get("runs_by_kind", {})),
            total_latency_ms=data.get("total_latency_ms", 0.0),
            last_run_at=datetime.fromisoformat(last_run_at) if last_run_at else None,
        )


class SyncStatisticsStore:
    """Loads/saves one `SyncStatistics` instance to `mt5_sync_statistics.json`
    under the package's own state dir -- same load/save idiom as
    `MT5Manager`/`BridgeExchangeManager`."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "mt5_sync_statistics.json"

    def load(self) -> SyncStatistics:
        file = self._file()
        if not file.exists():
            return SyncStatistics()
        try:
            return SyncStatistics.from_dict(json.loads(file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, KeyError):
            return SyncStatistics()

    def save(self, statistics: SyncStatistics) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._file().write_text(json.dumps(statistics.to_dict(), indent=2), encoding="utf-8")
