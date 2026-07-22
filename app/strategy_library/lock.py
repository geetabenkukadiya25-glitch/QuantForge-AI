"""Soft, single-machine editing lock (Phase 18 rule 28).

Prevents two editor sessions inside the SAME running app instance from
silently clobbering each other's saves -- e.g. two browser tabs open on
the same Streamlit server, each editing the same file. This is NOT a
distributed/multi-machine lock: the platform is offline and single-
process by design, so a local JSON lock file with a heartbeat + staleness
timeout is the right-sized mechanism (a stale lock -- e.g. a crashed
session -- is automatically reclaimable, so a real crash can never
permanently strand a strategy as "locked").
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.strategy_library.models import LockInfo
from app.utils.logger import get_logger

logger = get_logger(__name__)

#: A lock with no heartbeat in this long is treated as abandoned (crashed
#: session, closed tab, etc.) and may be silently reclaimed by anyone.
STALE_AFTER = timedelta(minutes=5)


class LockStore:
    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "locks.json"

    def _load(self) -> dict[str, LockInfo]:
        file = self._file()
        if not file.exists():
            return {}
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Lock file is unreadable; starting fresh.")
            return {}
        return {key: LockInfo.from_dict(value) for key, value in data.items()}

    def _save(self, locks: dict[str, LockInfo]) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._file().write_text(json.dumps({k: v.to_dict() for k, v in locks.items()}, indent=2), encoding="utf-8")

    def _is_stale(self, lock: LockInfo) -> bool:
        return datetime.now(timezone.utc) - lock.heartbeat_at > STALE_AFTER

    def acquire(self, key: str, owner_token: str) -> bool:
        """Returns True if `owner_token` now holds the lock (freshly
        acquired, already held, or reclaimed from a stale holder)."""
        locks = self._load()
        existing = locks.get(key)
        if existing is not None and existing.owner_token != owner_token and not self._is_stale(existing):
            return False
        now = datetime.now(timezone.utc)
        locks[key] = LockInfo(owner_token=owner_token, acquired_at=existing.acquired_at if existing and existing.owner_token == owner_token else now, heartbeat_at=now)
        self._save(locks)
        return True

    def heartbeat(self, key: str, owner_token: str) -> None:
        locks = self._load()
        existing = locks.get(key)
        if existing is not None and existing.owner_token == owner_token:
            locks[key] = LockInfo(owner_token=owner_token, acquired_at=existing.acquired_at, heartbeat_at=datetime.now(timezone.utc))
            self._save(locks)

    def release(self, key: str, owner_token: str) -> None:
        locks = self._load()
        existing = locks.get(key)
        if existing is not None and existing.owner_token == owner_token:
            del locks[key]
            self._save(locks)

    def holder(self, key: str) -> str | None:
        """The current lock holder's token, or `None` if unlocked/stale."""
        existing = self._load().get(key)
        if existing is None or self._is_stale(existing):
            return None
        return existing.owner_token

    def is_locked_by_other(self, key: str, owner_token: str) -> bool:
        holder = self.holder(key)
        return holder is not None and holder != owner_token
