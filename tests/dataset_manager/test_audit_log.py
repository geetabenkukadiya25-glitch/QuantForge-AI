"""`app.dataset_manager.audit_log.DatasetAuditLogStore` -- mirrors the
strategy_library audit_log tests exactly."""

from pathlib import Path

from app.dataset_manager.audit_log import DatasetAuditLogStore
from app.dataset_manager.models import DatasetAuditEventType


def test_record_and_list_events(tmp_path: Path) -> None:
    store = DatasetAuditLogStore(tmp_path)
    store.record(DatasetAuditEventType.IMPORTED, "abc123")
    store.record(DatasetAuditEventType.DELETED, "abc123")
    store.record(DatasetAuditEventType.IMPORTED, "other-id")

    events = store.list_events(key="abc123")
    assert [e.event_type for e in events] == [DatasetAuditEventType.DELETED, DatasetAuditEventType.IMPORTED]

    all_events = store.list_events()
    assert len(all_events) == 3


def test_list_events_on_missing_file_returns_empty(tmp_path: Path) -> None:
    store = DatasetAuditLogStore(tmp_path)
    assert store.list_events() == []


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = DatasetAuditLogStore(tmp_path)
    store.record(DatasetAuditEventType.IMPORTED, "abc123")
    (tmp_path / "dataset_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []
