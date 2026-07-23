"""`SyncHealth` (Phase 19.2) -- reports on synchronization ACTIVITY
(per-kind last-run status, run counts, average latency). Distinct from
`app.mt5.bridge_health.BridgeHealth` (bridge export/import counters)
and `app.mt5.mt5_models.HealthSnapshot` (terminal connection health) --
three different concerns, no duplication. Pure aggregation, no I/O.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.mt5_sync.sync_models import SyncRun, SyncStatus
from app.mt5_sync.sync_statistics import SyncStatistics


@dataclass(frozen=True)
class KindHealth:
    kind: str
    last_run_at: datetime | None
    last_status: str | None
    last_records_synced: int
    run_count: int
    failure_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "last_records_synced": self.last_records_synced,
            "run_count": self.run_count,
            "failure_count": self.failure_count,
        }


@dataclass(frozen=True)
class SyncHealth:
    overall_status: str  # "healthy" | "degraded" | "unknown"
    total_runs: int
    success_count: int
    failure_count: int
    average_latency_ms: float
    last_run_at: datetime | None
    connection_state: str
    per_kind: list[KindHealth] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_status": self.overall_status,
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "average_latency_ms": self.average_latency_ms,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "connection_state": self.connection_state,
            "per_kind": [k.to_dict() for k in self.per_kind],
        }


def build_sync_health(statistics: SyncStatistics, last_run_by_kind: dict[str, SyncRun], failure_count_by_kind: dict[str, int], connection_state: str) -> SyncHealth:
    if statistics.total_runs == 0:
        overall_status = "unknown"
    elif statistics.failure_count == 0:
        overall_status = "healthy"
    else:
        overall_status = "degraded"

    per_kind = [
        KindHealth(
            kind=kind,
            last_run_at=run.completed_at or run.started_at,
            last_status=run.status.value,
            last_records_synced=run.records_synced,
            run_count=statistics.runs_by_kind.get(kind, 0),
            failure_count=failure_count_by_kind.get(kind, 0),
        )
        for kind, run in sorted(last_run_by_kind.items())
    ]

    return SyncHealth(
        overall_status=overall_status,
        total_runs=statistics.total_runs,
        success_count=statistics.success_count,
        failure_count=statistics.failure_count,
        average_latency_ms=statistics.average_latency_ms,
        last_run_at=statistics.last_run_at,
        connection_state=connection_state,
        per_kind=per_kind,
    )
