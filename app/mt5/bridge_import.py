"""Import support (Phase 19.1) -- CONFIGURATION ONLY. `BridgeImportKind`
has no trade-related member, so a trade instruction is structurally
unrepresentable through the normal path; `parse_import` additionally
hard-rejects (raises `BridgeImportError`, never silently drops) any
payload carrying a forbidden trade-related keyword as defense in depth.
Every `apply_import` branch calls an existing, already-read-only
`MT5Manager` method -- nothing here mutates trading state.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from app.mt5.exceptions import BridgeImportError
from app.mt5.timeframe_manager import to_mt5_timeframe

if TYPE_CHECKING:
    from app.mt5.terminal_manager import MT5Manager

FORBIDDEN_KEYWORDS = frozenset({
    "trade", "buy", "sell", "modify", "close", "delete",
    "order_type", "order_send", "order_modify", "order_close",
    "positions_close", "execute", "execution", "lot", "sl", "tp",
})


class BridgeImportKind(str, Enum):
    SELECT_SYMBOL = "SELECT_SYMBOL"
    SET_TIMEFRAME = "SET_TIMEFRAME"
    HISTORY_REQUEST = "HISTORY_REQUEST"
    DIAGNOSTIC_REQUEST = "DIAGNOSTIC_REQUEST"
    HEALTH_REQUEST = "HEALTH_REQUEST"
    REFRESH_REQUEST = "REFRESH_REQUEST"


@dataclass(frozen=True)
class BridgeImportRequest:
    kind: BridgeImportKind
    params: dict[str, Any] = field(default_factory=dict)


def _scan_for_forbidden_keywords(obj: Any) -> str | None:
    """Recursively scans dict keys and string values (case-insensitive
    substring match) for anything in `FORBIDDEN_KEYWORDS`. Returns the
    first keyword found, or `None`."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(key, str):
                lowered_key = key.lower()
                for keyword in FORBIDDEN_KEYWORDS:
                    if keyword in lowered_key:
                        return keyword
            found = _scan_for_forbidden_keywords(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _scan_for_forbidden_keywords(item)
            if found:
                return found
    elif isinstance(obj, str):
        lowered_value = obj.lower()
        for keyword in FORBIDDEN_KEYWORDS:
            if keyword in lowered_value:
                return keyword
    return None


def parse_import(payload: dict[str, Any]) -> BridgeImportRequest:
    if not isinstance(payload, dict):
        raise BridgeImportError("Import payload must be a JSON object.")

    forbidden = _scan_for_forbidden_keywords(payload)
    if forbidden:
        raise BridgeImportError(f"Import payload rejected -- contains forbidden keyword '{forbidden}'. This bridge accepts configuration requests only, never trade instructions.")

    kind_raw = payload.get("kind")
    try:
        kind = BridgeImportKind(kind_raw)
    except ValueError:
        raise BridgeImportError(f"Unknown or missing import kind '{kind_raw}'. Supported: {', '.join(k.value for k in BridgeImportKind)}.")

    params = payload.get("params")
    if params is None:
        params = {}
    elif not isinstance(params, dict):
        raise BridgeImportError("Import payload 'params' must be a JSON object.")

    return BridgeImportRequest(kind=kind, params=params)


def apply_import(request: BridgeImportRequest, manager: "MT5Manager") -> dict[str, Any]:
    """Executes the read-only effect of an already-parsed, already-
    validated request. Every branch below is a read, never a write."""
    if request.kind == BridgeImportKind.SELECT_SYMBOL:
        symbol = request.params.get("symbol")
        if not symbol:
            raise BridgeImportError("SELECT_SYMBOL requires a 'symbol' param.")
        info = manager.get_symbol_info(symbol)
        return {"kind": request.kind.value, "acknowledged": True, "symbol": info.name}

    if request.kind == BridgeImportKind.SET_TIMEFRAME:
        timeframe = request.params.get("timeframe")
        if not timeframe:
            raise BridgeImportError("SET_TIMEFRAME requires a 'timeframe' param.")
        try:
            to_mt5_timeframe(timeframe)
        except ValueError as exc:
            raise BridgeImportError(str(exc)) from exc
        return {"kind": request.kind.value, "acknowledged": True, "timeframe": timeframe.upper()}

    if request.kind == BridgeImportKind.HISTORY_REQUEST:
        symbol = request.params.get("symbol")
        timeframe = request.params.get("timeframe", "H1")
        count = int(request.params.get("count", 100))
        if not symbol:
            raise BridgeImportError("HISTORY_REQUEST requires a 'symbol' param.")
        bars = manager.get_recent_history(symbol, timeframe, count)
        return {"kind": request.kind.value, "acknowledged": True, "bars": [b.to_dict() for b in bars]}

    if request.kind == BridgeImportKind.DIAGNOSTIC_REQUEST:
        report = manager.run_diagnostics()
        return {"kind": request.kind.value, "acknowledged": True, "all_passed": report.all_passed, "steps": [{"name": s.name, "passed": s.passed, "detail": s.detail} for s in report.steps]}

    if request.kind == BridgeImportKind.HEALTH_REQUEST:
        snapshot = manager.get_health_snapshot()
        return {"kind": request.kind.value, "acknowledged": True, "health": snapshot.to_dict()}

    if request.kind == BridgeImportKind.REFRESH_REQUEST:
        return {"kind": request.kind.value, "acknowledged": True, "connection_state": manager.connection_state.value}

    raise BridgeImportError(f"Unhandled import kind '{request.kind}'.")  # unreachable -- every enum member is handled above
