"""Sync scheduling (Phase 19.2) -- a pure query surface, mirroring
`app.cloud_sync.sync_scheduler`'s exact discipline. `SyncSchedule` is
metadata only; `due_schedules()` is a pure function nothing calls
automatically -- there is no timer thread, no background loop, no
"hidden execution" of any kind in this module.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.mt5_sync.sync_models import SyncKind


@dataclass
class SyncSchedule:
    kind: SyncKind
    interval_minutes: int
    enabled: bool = True
    last_run_at: datetime | None = None
    target: str = ""

    def is_due(self, now: datetime) -> bool:
        if not self.enabled:
            return False
        if self.last_run_at is None:
            return True
        return now - self.last_run_at >= timedelta(minutes=self.interval_minutes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "interval_minutes": self.interval_minutes,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "target": self.target,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SyncSchedule":
        last_run_at = data.get("last_run_at")
        return SyncSchedule(
            kind=SyncKind(data["kind"]),
            interval_minutes=data.get("interval_minutes", 15),
            enabled=data.get("enabled", True),
            last_run_at=datetime.fromisoformat(last_run_at) if last_run_at else None,
            target=data.get("target", ""),
        )


class SyncScheduler:
    """In-memory registry of `SyncSchedule`s + a pure `due_schedules`
    query. Nothing in this class -- or anywhere in `app.mt5_sync` --
    calls `due_schedules` automatically; there is no timer thread. A
    future UI/CLI/cron caller decides when (and whether) to act on
    what's due."""

    def __init__(self) -> None:
        self._schedules: list[SyncSchedule] = []

    def add(self, schedule: SyncSchedule) -> None:
        self._schedules.append(schedule)

    def list_schedules(self) -> list[SyncSchedule]:
        return list(self._schedules)

    def due_schedules(self, now: datetime) -> list[SyncSchedule]:
        return [s for s in self._schedules if s.is_due(now)]
