"""Sync schedule metadata (Phase 17.9) -- a pure query surface, not a
timer. Nothing in this project calls `SyncScheduler.due_schedules`
automatically; there is no background thread, no cron, no polling loop
anywhere in `app.cloud_sync`. A future real scheduler could call this
query and act on its result, but building that caller is explicitly out
of scope for this foundation phase.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.cloud_sync.cloud_models import SyncKind


@dataclass
class SyncSchedule:
    kind: SyncKind
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    interval_minutes: int = 60
    enabled: bool = True
    last_run_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "interval_minutes": self.interval_minutes,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
        }

    @staticmethod
    def from_dict(data: dict) -> "SyncSchedule":
        return SyncSchedule(
            id=data["id"],
            kind=SyncKind(data["kind"]),
            interval_minutes=data.get("interval_minutes", 60),
            enabled=data.get("enabled", True),
            last_run_at=datetime.fromisoformat(data["last_run_at"]) if data.get("last_run_at") else None,
        )

    def is_due(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        if self.last_run_at is None:
            return True
        elapsed_minutes = (now - self.last_run_at).total_seconds() / 60.0
        return elapsed_minutes >= self.interval_minutes


class SyncScheduler:
    def __init__(self, schedules: list[SyncSchedule] | None = None) -> None:
        self._schedules: list[SyncSchedule] = list(schedules or [])

    def add(self, schedule: SyncSchedule) -> None:
        self._schedules.append(schedule)

    def list_schedules(self) -> list[SyncSchedule]:
        return list(self._schedules)

    def due_schedules(self, now: datetime) -> list[SyncSchedule]:
        """Which schedules WOULD be due right now, if anything were
        actually calling this. Purely informational."""
        return [s for s in self._schedules if s.is_due(now)]
