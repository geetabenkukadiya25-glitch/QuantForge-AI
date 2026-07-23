"""`SettingsCenterManager` orchestrator (Phase 18.8) -- CRUD over the
single `SettingsState` document (mirrors `WorkflowManager`/`RiskManager`'s
JSON-state pattern), section validation, export/import/backup/restore
submitted as ordinary `JobManager` jobs (per spec), and path-override
storage. Never mutates `Settings`/`Paths` (both frozen/cached) and never
rewires any other module's runtime behavior -- see the package
docstring and Known Limitations in the final report.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config.paths import get_paths
from app.settings_center.audit import SettingsAuditEventType, SettingsAuditLogStore
from app.settings_center.backup import export_bytes, parse_import_bytes
from app.settings_center.exceptions import SettingsValidationError
from app.settings_center.settings_models import SECTION_TYPES, SettingsState
from app.utils.logger import get_logger

logger = get_logger(__name__)

_VALIDATORS = {
    "general": "app.settings_center.general",
    "datasets": "app.settings_center.datasets",
    "workflow": "app.settings_center.workflow",
    "jobs": "app.settings_center.jobs",
    "risk": "app.settings_center.risk",
    "charts": "app.settings_center.charts",
    "reports": "app.settings_center.reports",
    "notifications": "app.settings_center.notifications",
    "logging": "app.settings_center.logging",
}


def _section_module(name: str):
    import importlib

    if name not in _VALIDATORS:
        raise KeyError(f"Unknown settings section '{name}'.")
    return importlib.import_module(_VALIDATORS[name])


def _default_state() -> SettingsState:
    state = SettingsState()
    for name in SECTION_TYPES:
        setattr(state, name, _section_module(name).defaults())
    return state


class SettingsCenterManager:
    def __init__(self, state_dir: Path | None = None) -> None:
        paths = get_paths()
        self._state_dir = state_dir or paths.settings_center_state_dir
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._backups_dir = self._state_dir / "backups"
        self._audit_log = SettingsAuditLogStore(self._state_dir)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # State CRUD
    # ------------------------------------------------------------------

    def get_state(self) -> SettingsState:
        return self._load_state()

    def update_section(self, section_name: str, **fields) -> SettingsState:
        module = _section_module(section_name)  # raises KeyError for unknown section, surfaced as-is
        with self._lock:
            state = self._load_state()
            current = state.section(section_name)
            updated = type(current)(**{**current.to_dict(), **fields})
            issues = module.validate(updated)
            if issues:
                raise SettingsValidationError(issues)
            setattr(state, section_name, updated)
            state.version += 1
            state.updated_at = datetime.now()
            self._save_state(state)
        self._audit_log.record(SettingsAuditEventType.SECTION_UPDATED, section_name)
        return state

    def reset_section_to_defaults(self, section_name: str) -> SettingsState:
        module = _section_module(section_name)
        with self._lock:
            state = self._load_state()
            setattr(state, section_name, module.defaults())
            state.version += 1
            state.updated_at = datetime.now()
            self._save_state(state)
        self._audit_log.record(SettingsAuditEventType.RESET_TO_DEFAULTS, section_name)
        return state

    def reset_all_to_defaults(self) -> SettingsState:
        with self._lock:
            state = _default_state()
            state.version = self._load_state().version + 1
            self._save_state(state)
        self._audit_log.record(SettingsAuditEventType.RESET_TO_DEFAULTS, "*")
        return state

    # ------------------------------------------------------------------
    # Path overrides (stored preference only -- see module docstring)
    # ------------------------------------------------------------------

    def set_path_override(self, key: str, path: str) -> SettingsState:
        with self._lock:
            state = self._load_state()
            state.path_overrides[key] = path
            state.updated_at = datetime.now()
            self._save_state(state)
        self._audit_log.record(SettingsAuditEventType.PATH_CHANGED, key)
        return state

    def reset_path_override(self, key: str) -> SettingsState:
        with self._lock:
            state = self._load_state()
            state.path_overrides.pop(key, None)
            state.updated_at = datetime.now()
            self._save_state(state)
        self._audit_log.record(SettingsAuditEventType.PATH_RESET, key)
        return state

    # ------------------------------------------------------------------
    # Export / Import (synchronous + Job Manager-submitted variants)
    # ------------------------------------------------------------------

    def export_now(self) -> bytes:
        payload = export_bytes(self._load_state())
        self._audit_log.record(SettingsAuditEventType.EXPORTED, "settings")
        return payload

    def submit_export(self):
        from app.job_manager import JobCategory, get_job_manager

        def _op(job):
            with job.progress.step(0):
                return self.export_now()

        return get_job_manager().submit(name="Export Settings", category=JobCategory.OTHER, operation=_op, owner_page="Settings Center", step_names=["Exporting"])

    def import_now(self, data: bytes) -> SettingsState:
        imported = parse_import_bytes(data)  # raises SettingsImportError, never silently drops fields
        with self._lock:
            imported.version = self._load_state().version + 1
            imported.updated_at = datetime.now()
            self._save_state(imported)
        self._audit_log.record(SettingsAuditEventType.IMPORTED, "settings")
        return imported

    def submit_import(self, data: bytes):
        from app.job_manager import JobCategory, get_job_manager

        def _op(job):
            with job.progress.step(0):
                return self.import_now(data)

        return get_job_manager().submit(name="Import Settings", category=JobCategory.OTHER, operation=_op, owner_page="Settings Center", step_names=["Importing"])

    # ------------------------------------------------------------------
    # Backup / Restore (named snapshots on disk, synchronous + Job Manager-submitted)
    # ------------------------------------------------------------------

    def backup_now(self, label: str | None = None) -> str:
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        name = f"{timestamp}_{label}" if label else timestamp
        file = self._backups_dir / f"{name}.json"
        file.write_bytes(export_bytes(self._load_state()))
        self._audit_log.record(SettingsAuditEventType.BACKED_UP, name)
        return name

    def submit_backup(self, label: str | None = None):
        from app.job_manager import JobCategory, get_job_manager

        def _op(job):
            with job.progress.step(0):
                return self.backup_now(label)

        return get_job_manager().submit(name="Backup Settings", category=JobCategory.OTHER, operation=_op, owner_page="Settings Center", step_names=["Backing Up"])

    def list_backups(self) -> list[dict]:
        if not self._backups_dir.exists():
            return []
        entries = []
        for file in sorted(self._backups_dir.glob("*.json"), reverse=True):
            entries.append({"name": file.stem, "path": str(file), "modified": datetime.fromtimestamp(file.stat().st_mtime, tz=timezone.utc).isoformat()})
        return entries

    def restore_now(self, backup_name: str) -> SettingsState:
        file = self._backups_dir / f"{backup_name}.json"
        if not file.exists():
            raise FileNotFoundError(f"No backup named '{backup_name}'.")
        restored = parse_import_bytes(file.read_bytes())
        with self._lock:
            restored.version = self._load_state().version + 1
            restored.updated_at = datetime.now()
            self._save_state(restored)
        self._audit_log.record(SettingsAuditEventType.RESTORED, backup_name)
        return restored

    def submit_restore(self, backup_name: str):
        from app.job_manager import JobCategory, get_job_manager

        def _op(job):
            with job.progress.step(0):
                return self.restore_now(backup_name)

        return get_job_manager().submit(name="Restore Settings", category=JobCategory.OTHER, operation=_op, owner_page="Settings Center", step_names=["Restoring"])

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def list_audit_events(self, key: str | None = None, limit: int = 200):
        return self._audit_log.list_events(key=key, limit=limit)

    # ------------------------------------------------------------------
    # Internal persistence
    # ------------------------------------------------------------------

    def _state_file(self) -> Path:
        return self._state_dir / "settings_state.json"

    def _load_state(self) -> SettingsState:
        file = self._state_file()
        if not file.exists():
            state = _default_state()
            self._save_state(state)
            self._audit_log.record(SettingsAuditEventType.CREATED, "settings")
            return state
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Settings state file is unreadable; starting fresh.")
            return _default_state()
        return SettingsState.from_dict(data)

    def _save_state(self, state: SettingsState) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(state.to_dict(), indent=2), encoding="utf-8")
