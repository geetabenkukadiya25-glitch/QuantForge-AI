"""`app.data_catalog.audit_log.CatalogAuditLogStore` -- mirrors the
dataset_manager/strategy_library audit_log tests exactly."""

from pathlib import Path

from app.data_catalog.audit_log import CatalogAuditLogStore
from app.data_catalog.models import CatalogAuditEventType


def test_record_and_list_events(tmp_path: Path) -> None:
    store = CatalogAuditLogStore(tmp_path)
    store.record(CatalogAuditEventType.REFERENCED, "abc123")
    store.record(CatalogAuditEventType.DELETED, "abc123")
    store.record(CatalogAuditEventType.REFERENCED, "other-id")

    events = store.list_events(key="abc123")
    assert [e.event_type for e in events] == [CatalogAuditEventType.DELETED, CatalogAuditEventType.REFERENCED]

    all_events = store.list_events()
    assert len(all_events) == 3


def test_list_events_on_missing_file_returns_empty(tmp_path: Path) -> None:
    store = CatalogAuditLogStore(tmp_path)
    assert store.list_events() == []


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = CatalogAuditLogStore(tmp_path)
    store.record(CatalogAuditEventType.REFERENCED, "abc123")
    (tmp_path / "catalog_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []
