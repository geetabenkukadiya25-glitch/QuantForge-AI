"""`RiskAuditLogStore` -- mirrors `tests/workflow/test_audit_log.py`'s coverage."""

from pathlib import Path

from app.risk_analytics.audit import RiskAuditLogStore
from app.risk_analytics.risk_models import RiskAuditEventType


def test_record_and_list_events(tmp_path: Path) -> None:
    store = RiskAuditLogStore(tmp_path)
    store.record(RiskAuditEventType.ANALYZED, "r1")
    store.record(RiskAuditEventType.REPORT_GENERATED, "r1")
    store.record(RiskAuditEventType.ANALYZED, "r2")

    events = store.list_events("r1")
    assert len(events) == 2
    assert {e.event_type for e in events} == {RiskAuditEventType.ANALYZED, RiskAuditEventType.REPORT_GENERATED}


def test_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    store = RiskAuditLogStore(tmp_path)
    store.record(RiskAuditEventType.ANALYZED, "r1")
    (tmp_path / "risk_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    assert store.list_events() == []


def test_no_file_yet_returns_empty(tmp_path: Path) -> None:
    store = RiskAuditLogStore(tmp_path)
    assert store.list_events() == []
