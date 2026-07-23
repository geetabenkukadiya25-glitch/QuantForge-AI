"""`audit.py` -- verbatim mirror of `app.mt5.audit.MT5AuditLogStore`,
tested the same way."""

from pathlib import Path

from app.mt5_sync.audit import SyncAuditEventType, SyncAuditLogStore


def test_audit_log_records_and_lists_newest_first(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path)
    store.record(SyncAuditEventType.SYMBOL_SYNCED, "symbols")
    store.record(SyncAuditEventType.TICK_SYNCED, "EURUSD")
    events = store.list_events()
    assert len(events) == 2
    assert events[0].event_type == SyncAuditEventType.TICK_SYNCED


def test_audit_log_filters_by_key(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path)
    store.record(SyncAuditEventType.TICK_SYNCED, "EURUSD")
    store.record(SyncAuditEventType.TICK_SYNCED, "GBPUSD")
    assert len(store.list_events(key="EURUSD")) == 1


def test_audit_log_missing_file_returns_empty(tmp_path: Path) -> None:
    store = SyncAuditLogStore(tmp_path / "nonexistent")
    assert store.list_events() == []


def test_audit_log_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "mt5_sync_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    store = SyncAuditLogStore(tmp_path)
    assert store.list_events() == []
