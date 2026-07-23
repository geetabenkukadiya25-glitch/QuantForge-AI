"""Read-only accessors into the existing managers Governance references
by id (Phase 17.8) -- `WorkflowManager`, `RiskManager`, `DatasetManager`,
`StrategyLibraryManager`, `DataCatalog`. Every function here is a pure
read: none of them ever calls a mutating method (`sync()`,
`submit_run()`, `delete()`, ...) on the module it looks into, and every
call is wrapped defensively (mirrors `command_bar.py`'s "recents"
sections) so a missing/renamed object never crashes Governance -- it
just resolves to `None`/`False`, the same honest-non-fabrication
convention used throughout this project.

`STRATEGY` objects are referenced by `LibraryEntry.path` (a relative,
portable path string) rather than `strategy_id` -- `StrategyLibraryManager`
itself is keyed that way, since a file can be renamed/duplicated
independently of its declared SDL id.
"""

from app.governance.governance_models import GovernedObjectType


def resolve_object_label(object_type: GovernedObjectType, object_id: str) -> str | None:
    """Best-effort human-readable label for `object_id` -- `None` if the
    object can't currently be resolved (doesn't exist, or its owning
    module has no durable id-lookup for this object type)."""
    try:
        if object_type == GovernedObjectType.DATASET:
            from app.dataset_manager import DatasetManager

            return DatasetManager().get(object_id).display_name
        if object_type == GovernedObjectType.WORKFLOW:
            from app.workflow import get_workflow_manager

            return get_workflow_manager().get(object_id).name
        if object_type == GovernedObjectType.RISK_REPORT:
            from app.risk_analytics import get_risk_manager

            return get_risk_manager().get_report(object_id).title
        if object_type == GovernedObjectType.STRATEGY:
            from app.strategy_library import StrategyLibraryManager

            for entry in StrategyLibraryManager().list_entries():
                if str(entry.path) == object_id:
                    return entry.name
            return None
    except Exception:  # noqa: BLE001 -- a resolution failure must never crash Governance over an optional label
        return None
    return None


def workflow_run_status(object_id: str) -> str | None:
    """Latest run status for a governed WORKFLOW, or `None` if it has no
    runs yet / can't be resolved."""
    try:
        from app.workflow import get_workflow_manager

        runs = get_workflow_manager().run_history(workflow_id=object_id, limit=1)
        return runs[0].status.value if runs else None
    except Exception:  # noqa: BLE001
        return None


def linked_risk_reports(object_id: str) -> list[str]:
    """Ids of risk reports whose `source_description`/`tags` reference
    `object_id` -- a best-effort text match, since Risk Analytics has no
    formal foreign-key link back to the object it analyzed."""
    try:
        from app.risk_analytics import get_risk_manager

        return [r.id for r in get_risk_manager().list_reports() if object_id in r.source_description or object_id in r.tags]
    except Exception:  # noqa: BLE001
        return []


def object_exists(object_type: GovernedObjectType, object_id: str) -> bool:
    """`True` only for the 5 durably-persisted object types this project
    currently supports id-lookups for (Strategy/Dataset/Workflow/Risk
    Report/Portfolio-as-Workflow); Experiment/Research Report/Export/
    Portfolio have no durable id today (see Known Limitations), so this
    always returns `True` for them -- existence simply can't be verified,
    not disproven."""
    if object_type in (GovernedObjectType.EXPERIMENT, GovernedObjectType.RESEARCH_REPORT, GovernedObjectType.EXPORT, GovernedObjectType.PORTFOLIO):
        return True
    return resolve_object_label(object_type, object_id) is not None
