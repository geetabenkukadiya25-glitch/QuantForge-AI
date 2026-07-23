"""Institutional Settings Center (Phase 18.8) -- the canonical, persisted
store for user-facing configuration across General/Datasets/Workflow/
Jobs/Risk/Charts/Reports/Notifications/Logging/Paths, plus Backup
(export/import/reset) and About. Never modifies any engine, Job Manager,
Dataset Manager, Data Catalog, Workflow, Risk Analytics, Governance,
Strategy Library, or SDL module, and never mutates the existing frozen
`Settings`/`Paths` singletons. This phase does not rewire any other
module to read from here -- see Known Limitations in the final report.
Long-running Export/Import/Backup/Restore actions run as ordinary
`JobManager` jobs.
"""

import threading

from app.settings_center.exceptions import SettingsError, SettingsImportError, SettingsValidationError
from app.settings_center.settings_manager import SettingsCenterManager
from app.settings_center.settings_models import SettingsState

_singleton: SettingsCenterManager | None = None
_singleton_lock = threading.Lock()


def get_settings_center_manager() -> SettingsCenterManager:
    """The process-wide `SettingsCenterManager` singleton -- mirrors
    `get_governance_manager()`/`get_risk_manager()`/`get_job_manager()`."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = SettingsCenterManager()
    return _singleton


__all__ = [
    "SettingsCenterManager",
    "get_settings_center_manager",
    "SettingsState",
    "SettingsError",
    "SettingsValidationError",
    "SettingsImportError",
]
