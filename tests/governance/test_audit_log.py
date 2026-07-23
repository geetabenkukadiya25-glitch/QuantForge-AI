"""`GovernanceAuditLogStore` -- mirrors `tests/workflow/test_audit_log.py`'s coverage."""

from pathlib import Path

from app.governance.audit import GovernanceAuditEventType, GovernanceAuditLogStore


def test_record_and_list_events(tmp_path: Path) -> None:
    store = GovernanceAuditLogStore(tmp_path)
    store.record(GovernanceAuditEventType.CREATED, "r1")
    store.record(GovernanceAuditEventType.APPROVED, "r1")
    store.record(GovernanceAuditEventType.CREATED, "r2")

    events = store.list_events("r1")
    assert len(events) == 2
    assert {e.event_type for e in events} == {GovernanceAuditEventType.CREATED, GovernanceAuditEventType.APPROVED}


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = GovernanceAuditLogStore(tmp_path)
    store.record(GovernanceAuditEventType.CREATED, "r1")
    (tmp_path / "governance_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = GovernanceAuditLogStore(tmp_path)
    assert store.list_events() == []
