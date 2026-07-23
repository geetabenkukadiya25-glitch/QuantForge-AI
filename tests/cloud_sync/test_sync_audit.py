"""`SyncAuditLogStore` -- mirrors `tests/governance/test_audit_log.py`'s coverage."""

from pathlib import Path

from app.cloud_sync.sync_audit import SyncAuditEventType, SyncAuditLogStore


def test_record_and_list_events(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path)
    store.record(SyncAuditEventType.CREATED, "op-1")
    store.record(SyncAuditEventType.COMPLETED, "op-1")
    store.record(SyncAuditEventType.CREATED, "op-2")

    events = store.list_events("op-1")
    assert len(events) == 2
    assert {e.event_type for e in events} == {SyncAuditEventType.CREATED, SyncAuditEventType.COMPLETED}


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path)
    store.record(SyncAuditEventType.CREATED, "op-1")
    (tmp_path / "cloud_sync_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path)
    assert store.list_events() == []
