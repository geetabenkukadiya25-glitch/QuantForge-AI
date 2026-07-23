"""Thin export/import wrappers per dataclass (Phase 19.0), mirrors
`app.governance.serializer`/`app.cloud_sync.sync_serializer` -- no
`json.dumps`/`json.loads` inside them, just `to_dict`/`from_dict` calls.
"""

from typing import Any

from app.mt5.mt5_models import AccountInfo, Bar, HealthSnapshot, SymbolInfo, TerminalInfo, Tick


def export_terminal_info(info: TerminalInfo) -> dict[str, Any]:
    return info.to_dict()


def import_terminal_info(data: dict[str, Any]) -> TerminalInfo:
    return TerminalInfo.from_dict(data)


def export_account_info(info: AccountInfo) -> dict[str, Any]:
    return info.to_dict()


def import_account_info(data: dict[str, Any]) -> AccountInfo:
    return AccountInfo.from_dict(data)


def export_symbol_info(info: SymbolInfo) -> dict[str, Any]:
    return info.to_dict()


def import_symbol_info(data: dict[str, Any]) -> SymbolInfo:
    return SymbolInfo.from_dict(data)


def export_bar(bar: Bar) -> dict[str, Any]:
    return bar.to_dict()


def import_bar(data: dict[str, Any]) -> Bar:
    return Bar.from_dict(data)


def export_tick(tick: Tick) -> dict[str, Any]:
    return tick.to_dict()


def import_tick(data: dict[str, Any]) -> Tick:
    return Tick.from_dict(data)


def export_health_snapshot(snapshot: HealthSnapshot) -> dict[str, Any]:
    return snapshot.to_dict()


def import_health_snapshot(data: dict[str, Any]) -> HealthSnapshot:
    return HealthSnapshot.from_dict(data)
