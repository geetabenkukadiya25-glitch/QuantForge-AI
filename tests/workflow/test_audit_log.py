"""`WorkflowAuditLogStore` (Phase 17.6) -- mirrors
`tests/dataset_manager/test_audit_log.py`'s coverage."""

from pathlib import Path

from app.workflow.audit_log import WorkflowAuditEventType, WorkflowAuditLogStore


def test_record_and_list_events(tmp_path: Path) -> None:
    store = WorkflowAuditLogStore(tmp_path)
    store.record(WorkflowAuditEventType.CREATED, "wf1")
    store.record(WorkflowAuditEventType.QUEUED, "wf1")
    store.record(WorkflowAuditEventType.CREATED, "wf2")

    events = store.list_events("wf1")
    assert len(events) == 2
    assert {e.event_type for e in events} == {WorkflowAuditEventType.CREATED, WorkflowAuditEventType.QUEUED}


def test_list_events_without_key_returns_everything(tmp_path: Path) -> None:
    store = WorkflowAuditLogStore(tmp_path)
    store.record(WorkflowAuditEventType.CREATED, "wf1")
    store.record(WorkflowAuditEventType.CREATED, "wf2")
    assert len(store.list_events()) == 2


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = WorkflowAuditLogStore(tmp_path)
    store.record(WorkflowAuditEventType.CREATED, "wf1")
    (tmp_path / "workflow_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = WorkflowAuditLogStore(tmp_path)
    assert store.list_events() == []
