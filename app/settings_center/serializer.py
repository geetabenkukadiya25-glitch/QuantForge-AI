"""JSON round-trip for `SettingsState` (Phase 18.8) -- mirrors
`app.governance.serializer`/`app.workflow.workflow_serializer` exactly:
thin `dict`-returning wrappers, no `json.dumps`/`json.loads` here."""

from app.settings_center.settings_models import SettingsState


def export_settings(state: SettingsState) -> dict:
    return state.to_dict()


def import_settings(data: dict) -> SettingsState:
    return SettingsState.from_dict(data)
