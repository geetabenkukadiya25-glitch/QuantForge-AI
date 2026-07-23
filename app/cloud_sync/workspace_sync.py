"""Read-only accessors into the 6 real managers Cloud Sync references by
id (Phase 17.9) -- verbatim mirror of `app.governance.workflow_hooks`'s
defensive shape: one function per concern, local import of the target
manager inside the function body, a single broad
`except Exception:  # noqa: BLE001` per function, returns
`None`/`False` on failure, never raises. None of these functions ever
call a mutating method on any target manager.

`SETTINGS` is a singleton document (no per-id lookup) -- `object_id` is
ignored for that kind and the label/payload are always resolved from
`SettingsCenterManager.get_state()`.
"""

from app.cloud_sync.cloud_models import SyncKind


def resolve_object_label(kind: SyncKind, object_id: str) -> str | None:
    try:
        if kind == SyncKind.DATASET:
            from app.dataset_manager import DatasetManager

            return DatasetManager().get(object_id).display_name
        if kind == SyncKind.STRATEGY:
            from app.strategy_library import StrategyLibraryManager

            for entry in StrategyLibraryManager().list_entries():
                if str(entry.path) == object_id:
                    return entry.name
            return None
        if kind == SyncKind.WORKFLOW:
            from app.workflow import get_workflow_manager

            return get_workflow_manager().get(object_id).name
        if kind == SyncKind.RISK_REPORT:
            from app.risk_analytics import get_risk_manager

            return get_risk_manager().get_report(object_id).title
        if kind == SyncKind.GOVERNANCE_RECORD:
            from app.governance import get_governance_manager

            record = get_governance_manager().get(object_id)
            return record.object_label or record.object_id
        if kind == SyncKind.SETTINGS:
            from app.settings_center import get_settings_center_manager

            return get_settings_center_manager().get_state().general.project_name
    except Exception:  # noqa: BLE001 -- a resolution failure must never crash Cloud Sync over an optional label
        return None
    return None


def object_exists(kind: SyncKind, object_id: str) -> bool:
    if kind in (SyncKind.ARTIFACT, SyncKind.SNAPSHOT, SyncKind.SETTINGS):
        return True  # SETTINGS is a singleton (always "exists"); ARTIFACT/SNAPSHOT are Cloud Sync's own records, checked by the manager directly
    return resolve_object_label(kind, object_id) is not None


def resolve_object_payload(kind: SyncKind, object_id: str) -> dict | None:
    """Best-effort JSON-serializable snapshot of the object's current
    content, used only to feed `artifact.register_artifact`'s content
    hash -- never mutated, never written back anywhere."""
    try:
        if kind == SyncKind.DATASET:
            from app.dataset_manager import DatasetManager

            record = DatasetManager().get(object_id)
            return {"id": record.id, "display_name": record.display_name, "filename": record.filename}
        if kind == SyncKind.STRATEGY:
            from app.strategy_library import StrategyLibraryManager

            for entry in StrategyLibraryManager().list_entries():
                if str(entry.path) == object_id:
                    return {"path": str(entry.path), "name": entry.name, "strategy_version": entry.strategy_version}
            return None
        if kind == SyncKind.WORKFLOW:
            from app.workflow import get_workflow_manager

            return get_workflow_manager().get(object_id).to_dict()
        if kind == SyncKind.RISK_REPORT:
            from app.risk_analytics import get_risk_manager

            return get_risk_manager().get_report(object_id).to_dict()
        if kind == SyncKind.GOVERNANCE_RECORD:
            from app.governance import get_governance_manager

            return get_governance_manager().get(object_id).to_dict()
        if kind == SyncKind.SETTINGS:
            from app.settings_center import get_settings_center_manager

            return get_settings_center_manager().get_state().to_dict()
    except Exception:  # noqa: BLE001 -- a resolution failure must never crash Cloud Sync over an optional payload
        return None
    return None
