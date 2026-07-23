"""Pure bytes-level export/import/validation logic for the Settings
Center (Phase 18.8). No `JobManager` here -- job submission is a
manager-level concern, mirroring `RiskManager`/`GovernanceManager`,
which keep `submit_*` on the manager itself rather than in a helper
module."""

import json

from app.settings_center.exceptions import SettingsImportError
from app.settings_center.serializer import export_settings, import_settings
from app.settings_center.settings_models import SettingsState

_REQUIRED_SECTIONS = ("general", "datasets", "workflow", "jobs", "risk", "charts", "reports", "notifications", "logging")


def export_bytes(state: SettingsState) -> bytes:
    return json.dumps(export_settings(state), indent=2).encode("utf-8")


def validate_import_payload(data: dict) -> list[str]:
    issues = []
    if not isinstance(data, dict):
        return ["payload must be a JSON object"]
    for section in _REQUIRED_SECTIONS:
        if section not in data:
            issues.append(f"missing required section '{section}'")
        elif not isinstance(data[section], dict):
            issues.append(f"section '{section}' must be an object")
    return issues


def parse_import_bytes(data: bytes) -> SettingsState:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SettingsImportError([f"payload is not valid JSON: {exc}"]) from exc
    issues = validate_import_payload(payload)
    if issues:
        raise SettingsImportError(issues)
    return import_settings(payload)
