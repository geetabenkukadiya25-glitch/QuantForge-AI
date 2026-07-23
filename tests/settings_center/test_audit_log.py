"""`SettingsAuditLogStore` -- mirrors `tests/governance/test_audit_log.py`'s coverage."""

from pathlib import Path

from app.settings_center.audit import SettingsAuditEventType, SettingsAuditLogStore


def test_record_and_list_events(tmp_path: Path) -> None:
    store = SettingsAuditLogStore(tmp_path)
    store.record(SettingsAuditEventType.CREATED, "settings")
    store.record(SettingsAuditEventType.SECTION_UPDATED, "risk")
    store.record(SettingsAuditEventType.SECTION_UPDATED, "charts")

    events = store.list_events("risk")
    assert len(events) == 1
    assert events[0].event_type == SettingsAuditEventType.SECTION_UPDATED


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = SettingsAuditLogStore(tmp_path)
    store.record(SettingsAuditEventType.CREATED, "settings")
    (tmp_path / "settings_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = SettingsAuditLogStore(tmp_path)
    assert store.list_events() == []
