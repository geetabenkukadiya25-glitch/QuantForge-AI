"""JSON round-trip for a single `GovernanceRecord` (Phase 17.8) --
mirrors `app.workflow.workflow_serializer` exactly.
"""

from app.governance.governance_models import GovernanceRecord


def export_record(record: GovernanceRecord) -> dict:
    return record.to_dict()


def import_record(data: dict) -> GovernanceRecord:
    return GovernanceRecord.from_dict(data)
