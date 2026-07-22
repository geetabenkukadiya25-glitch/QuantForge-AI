"""Local autosave + crash recovery (Phase 18 rules 26 & 27).

Autosaves are written ONLY under `Paths.sdl_autosave_dir` -- the original
strategy file is never touched by autosave. On next launch, any autosave
whose content still differs from the (now-current) original is offered
back to the user as "Recovered Strategy Found" (Restore / Discard /
Compare) by the UI layer, using `list_recoverable()` here.

Streamlit has no persistent background timer -- "every 30 seconds" is
approximated by the UI layer checking elapsed wall-clock time on each
script rerun (a `st.session_state` timestamp), which is the closest
offline, dependency-free equivalent available to a synchronous,
rerun-per-interaction app. This module only implements the storage half.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.strategy_library.models import AutosaveRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AutosaveStore:
    """One autosave slot per original strategy key (`None` key = a
    not-yet-saved new/duplicated strategy), each holding the single most
    recent snapshot -- not a history (that's `VersionSnapshot`'s job)."""

    def __init__(self, autosave_dir: Path) -> None:
        self._dir = autosave_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _index_file(self) -> Path:
        return self._dir / "index.json"

    def _load_index(self) -> dict[str, str]:
        """slot_key -> content filename."""
        file = self._index_file()
        if not file.exists():
            return {}
        try:
            return json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Autosave index is unreadable; starting fresh.")
            return {}

    def _save_index(self, index: dict[str, str]) -> None:
        self._index_file().write_text(json.dumps(index, indent=2), encoding="utf-8")

    @staticmethod
    def _slot_key(original_key: str | None, session_token: str) -> str:
        return original_key or f"__new__:{session_token}"

    def save(self, original_key: str | None, session_token: str, fmt: Literal["yaml", "json"], content: str) -> AutosaveRecord:
        slot_key = self._slot_key(original_key, session_token)
        record = AutosaveRecord(key=slot_key, saved_at=datetime.now(timezone.utc), fmt=fmt, content=content, original_key=original_key)
        filename = f"{abs(hash(slot_key))}.json"
        (self._dir / filename).write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        index = self._load_index()
        index[slot_key] = filename
        self._save_index(index)
        return record

    def get(self, original_key: str | None, session_token: str) -> AutosaveRecord | None:
        index = self._load_index()
        filename = index.get(self._slot_key(original_key, session_token))
        if filename is None:
            return None
        file = self._dir / filename
        if not file.exists():
            return None
        return AutosaveRecord.from_dict(json.loads(file.read_text(encoding="utf-8")))

    def discard(self, original_key: str | None, session_token: str) -> None:
        index = self._load_index()
        slot_key = self._slot_key(original_key, session_token)
        filename = index.pop(slot_key, None)
        if filename is not None:
            (self._dir / filename).unlink(missing_ok=True)
            self._save_index(index)

    def list_all(self) -> list[AutosaveRecord]:
        """Every autosave slot currently on disk, across all sessions --
        used at app startup to detect crash-recoverable work."""
        index = self._load_index()
        records = []
        for filename in index.values():
            file = self._dir / filename
            if file.exists():
                try:
                    records.append(AutosaveRecord.from_dict(json.loads(file.read_text(encoding="utf-8"))))
                except (json.JSONDecodeError, OSError):
                    continue
        return records
