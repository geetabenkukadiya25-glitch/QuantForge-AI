"""JSON export/import for one `Workflow` definition (Phase 17.6) --
backup or sharing a pipeline between installs. Thin wrapper over
`Workflow.to_dict`/`from_dict`; never round-trips run history."""

from app.workflow.workflow_models import Workflow


def export_workflow(workflow: Workflow) -> dict:
    return workflow.to_dict()


def import_workflow(data: dict) -> Workflow:
    return Workflow.from_dict(data)
