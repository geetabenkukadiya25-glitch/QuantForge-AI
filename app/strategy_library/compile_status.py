"""Per-strategy compile status tracking (Phase 18 rule 22).

Records the outcome of `StrategyCompiler.compile()` attempts -- success/
failure, duration, timestamp -- WITHOUT modifying `StrategyCompiler`
itself. The manager calls `record()` around its own (unmodified) call to
the compiler; this module only persists what happened.
"""

import json
from pathlib import Path

from app.strategy_library.models import CompileRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompileStatusStore:
    """A single JSON file mapping strategy state-key -> `CompileRecord`."""

    def __init__(self, state_dir: Path) -> None:
        self._state_dir = state_dir

    def _file(self) -> Path:
        return self._state_dir / "compile_status.json"

    def _load(self) -> dict[str, CompileRecord]:
        file = self._file()
        if not file.exists():
            return {}
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Compile status file is unreadable; starting fresh.")
            return {}
        return {key: CompileRecord.from_dict(value) for key, value in data.items()}

    def _save(self, records: dict[str, CompileRecord]) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._file().write_text(json.dumps({k: v.to_dict() for k, v in records.items()}, indent=2), encoding="utf-8")

    def record(self, key: str, record: CompileRecord) -> None:
        records = self._load()
        records[key] = record
        self._save(records)

    def get(self, key: str) -> CompileRecord | None:
        return self._load().get(key)

    def clear(self, key: str) -> None:
        records = self._load()
        if key in records:
            del records[key]
            self._save(records)

    def rename_key(self, old_key: str, new_key: str) -> None:
        records = self._load()
        if old_key in records:
            records[new_key] = records.pop(old_key)
            self._save(records)
