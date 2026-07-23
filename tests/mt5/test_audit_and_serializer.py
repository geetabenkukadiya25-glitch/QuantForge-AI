"""`audit.py`/`serializer.py` -- verbatim mirrors of the Governance
patterns, tested the same way `tests/governance/test_audit.py` does."""

from pathlib import Path

from app.mt5.audit import MT5AuditEventType, MT5AuditLogStore
from app.mt5.mt5_models import AccountInfo, TerminalInfo
from app.mt5.serializer import export_account_info, export_terminal_info, import_account_info, import_terminal_info


def test_audit_log_records_and_lists(tmp_path: Path) -> None:
    store = MT5AuditLogStore(tmp_path)
    store.record(MT5AuditEventType.CONNECTED, "connection")
    store.record(MT5AuditEventType.PING, "connection")
    events = store.list_events()
    assert len(events) == 2
    assert events[0].event_type == MT5AuditEventType.PING  # newest first


def test_audit_log_filters_by_key(tmp_path: Path) -> None:
    store = MT5AuditLogStore(tmp_path)
    store.record(MT5AuditEventType.CONNECTED, "connection")
    store.record(MT5AuditEventType.HISTORY_SYNCED, "EURUSD")
    assert len(store.list_events(key="EURUSD")) == 1


def test_audit_log_missing_file_returns_empty(tmp_path: Path) -> None:
    store = MT5AuditLogStore(tmp_path / "nonexistent")
    assert store.list_events() == []


def test_audit_log_corrupt_file_degrades_gracefully(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "mt5_audit_log.jsonl").write_text("not json\n", encoding="utf-8")
    store = MT5AuditLogStore(tmp_path)
    assert store.list_events() == []


def test_terminal_info_serializer_round_trip() -> None:
    info = TerminalInfo(community_account=False, connected=True, trade_allowed=True, trade_expert=False, build=6033, name="MT5", company="MetaQuotes", path="p", data_path="d")
    assert import_terminal_info(export_terminal_info(info)) == info


def test_account_info_serializer_round_trip() -> None:
    info = AccountInfo(login=1, server="s", currency="USD", balance=1.0, equity=1.0, margin=0.0, margin_free=1.0, leverage=1, trade_allowed=True)
    assert import_account_info(export_account_info(info)) == info
