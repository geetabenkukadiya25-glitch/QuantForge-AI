"""Builds the combined JSON Bridge document (Phase 19.1) from real,
already-available `MT5Manager` read-only calls. Every section degrades
honestly (`{"available": False, "reason": "..."}`) rather than either
raising past this function or fabricating a value when the terminal
isn't connected or a call fails -- "never fabricate connection" extends
to "never fabricate a field."
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from app.core.checksums import compute_checksum
from app.mt5.bridge_protocol import BRIDGE_SCHEMA_VERSION
from app.mt5.exceptions import MT5Error
from app.mt5.mt5_models import ConnectionState
from app.mt5.serializer import export_account_info, export_health_snapshot, export_terminal_info

if TYPE_CHECKING:
    from app.mt5.terminal_manager import MT5Manager

DEFAULT_SECTIONS = frozenset({"terminal", "account", "symbols", "positions", "orders", "health", "diagnostics", "compatibility"})


def _safe(fn, *, list_valued: bool = False) -> Any:
    """Runs `fn()`, degrading honestly on an `MT5Error` instead of
    raising past this function or fabricating a value. The degrade
    shape must match the field's declared type in `bridge_validator.
    KNOWN_FIELDS` -- a `list`-typed field degrades to `[]` (an empty
    list is itself a valid, non-fabricated "nothing available" answer),
    a `dict`-typed field degrades to `{"available": False, "reason": ...}`."""
    try:
        return fn()
    except MT5Error as exc:
        return [] if list_valued else {"available": False, "reason": str(exc)}


def export_document(
    manager: "MT5Manager",
    include: set[str] | None = None,
    history_symbol: str | None = None,
    history_timeframe: str = "H1",
    history_count: int = 100,
    tick_symbol: str | None = None,
    tick_count: int = 100,
) -> dict[str, Any]:
    """Builds the combined document. `include` restricts which of
    `DEFAULT_SECTIONS` are populated (defaults to all of them);
    `history`/`ticks` are only populated when a symbol is explicitly
    supplied, since they require a bounded request, not just "connect
    and go". The `checksum` field is computed last, over every other
    field -- it is never itself part of what it hashes.
    """
    sections = DEFAULT_SECTIONS if include is None else (include & DEFAULT_SECTIONS)
    document: dict[str, Any] = {
        "version": BRIDGE_SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if "terminal" in sections:
        document["terminal"] = _safe(lambda: export_terminal_info(manager.get_terminal_info()))
    if "account" in sections:
        document["account"] = _safe(lambda: export_account_info(manager.get_account_info()))
    if "symbols" in sections:
        document["symbols"] = _safe(lambda: [s.to_dict() for s in manager.list_symbols() if s.visible], list_valued=True)
    if "positions" in sections:
        document["positions"] = _safe(lambda: [p.to_dict() for p in manager.get_positions()], list_valued=True)
    if "orders" in sections:
        document["orders"] = _safe(lambda: [o.to_dict() for o in manager.get_orders()], list_valued=True)
    if "health" in sections:
        document["health"] = _safe(lambda: export_health_snapshot(manager.get_health_snapshot()))
    if "diagnostics" in sections:
        document["diagnostics"] = _safe(lambda: _diagnostics_to_dict(manager))
    if "compatibility" in sections:
        document["compatibility"] = _safe(lambda: _compatibility_to_dict(manager))

    if history_symbol and manager.connection_state == ConnectionState.CONNECTED:
        document["history"] = _safe(
            lambda: [b.to_dict() for b in manager.get_recent_history(history_symbol, history_timeframe, history_count)],
            list_valued=True,
        )
    if tick_symbol and manager.connection_state == ConnectionState.CONNECTED:
        document["ticks"] = _safe(lambda: [t.to_dict() for t in manager.get_recent_ticks(tick_symbol, tick_count)], list_valued=True)

    document["checksum"] = compute_checksum(document)
    return document


def _diagnostics_to_dict(manager: "MT5Manager") -> dict[str, Any]:
    report = manager.run_diagnostics()
    return {
        "all_passed": report.all_passed,
        "steps": [{"name": s.name, "passed": s.passed, "detail": s.detail} for s in report.steps],
    }


def _compatibility_to_dict(manager: "MT5Manager") -> dict[str, Any]:
    result = manager.compatibility()
    return {
        "package_version": result.package_version,
        "package_supported": result.package_supported,
        "terminal_build": result.terminal_build,
        "terminal_supported": result.terminal_supported,
        "notes": result.notes,
    }


