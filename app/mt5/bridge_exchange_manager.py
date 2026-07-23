"""`BridgeExchangeManager` (Phase 19.1) -- the stateful JSON Bridge
orchestrator. Composes `MT5Manager` (via `get_mt5_manager()`),
`bridge_export`, `bridge_import`, `bridge_validator`, `bridge_health`,
and the *existing* `bridge_manager.py` free functions and `audit.py`
store -- nothing here re-implements what those already provide. Persists
its own tiny counters file, separate from `MT5ManagerState`'s, so that
file's schema is never touched.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.mt5 import bridge_manager
from app.mt5.audit import MT5AuditEventType, MT5AuditLogStore
from app.mt5.bridge_export import export_document
from app.mt5.bridge_health import BridgeHealth, build_bridge_health
from app.mt5.bridge_import import BridgeImportRequest, apply_import, parse_import
from app.mt5.bridge_serializer import deserialize
from app.mt5.bridge_validator import validate_document, validate_json
from app.mt5.exceptions import BridgeImportError, MT5Error
from app.mt5.mt5_models import BridgeExchangeState
from app.mt5.terminal_health import BRIDGE_VERSION


class ImportResult:
    """Not a persisted dataclass -- just the return shape of
    `import_request`, mirroring how other managers return a small
    result object without needing `to_dict`/`from_dict`."""

    def __init__(self, success: bool, issues: list[str], result: dict[str, Any] | None) -> None:
        self.success = success
        self.issues = issues
        self.result = result


_BRIDGE_AUDIT_KINDS = frozenset({
    MT5AuditEventType.BRIDGE_EXPORTED,
    MT5AuditEventType.BRIDGE_IMPORTED,
    MT5AuditEventType.BRIDGE_VALIDATION_FAILED,
    MT5AuditEventType.BRIDGE_SCHEMA_MISMATCH,
})


class BridgeExchangeManager:
    def __init__(self, state_dir: Path, manager=None) -> None:
        self._state_dir = state_dir
        self._manager = manager
        self._audit = MT5AuditLogStore(state_dir)  # same audit store class/dir as MT5Manager -- one shared log, no second store
        self._lock = threading.Lock()
        self._state = self._load_state()

    @property
    def _mt5_manager(self):
        if self._manager is not None:
            return self._manager
        from app.mt5 import get_mt5_manager

        return get_mt5_manager()

    # ------------------------------------------------------------------
    # Local state persistence (own counters only -- separate file)
    # ------------------------------------------------------------------

    def _state_file(self) -> Path:
        return self._state_dir / "mt5_bridge_state.json"

    def _load_state(self) -> BridgeExchangeState:
        file = self._state_file()
        if not file.exists():
            return BridgeExchangeState()
        try:
            return BridgeExchangeState.from_dict(json.loads(file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError, KeyError):
            return BridgeExchangeState()

    def _save_state(self) -> None:
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file().write_text(json.dumps(self._state.to_dict(), indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self,
        include: set[str] | None = None,
        history_symbol: str | None = None,
        history_timeframe: str = "H1",
        history_count: int = 100,
        tick_symbol: str | None = None,
        tick_count: int = 100,
    ) -> dict[str, Any]:
        document = export_document(
            self._mt5_manager,
            include=include,
            history_symbol=history_symbol,
            history_timeframe=history_timeframe,
            history_count=history_count,
            tick_symbol=tick_symbol,
            tick_count=tick_count,
        )
        with self._lock:
            self._state.export_count += 1
            self._state.last_export_at = datetime.now(timezone.utc)
            self._save_state()
        self._audit.record(MT5AuditEventType.BRIDGE_EXPORTED, f"checksum:{document.get('checksum', '')[:12]}")
        return document

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, raw_or_document: str | dict[str, Any]) -> list[str]:
        issues = validate_json(raw_or_document) if isinstance(raw_or_document, str) else validate_document(raw_or_document)
        with self._lock:
            self._state.last_validation_at = datetime.now(timezone.utc)
            self._state.last_validation_ok = not issues
            self._save_state()
        if issues:
            summary = "; ".join(issues)[:200]
            event_type = MT5AuditEventType.BRIDGE_SCHEMA_MISMATCH if any("schema version" in i for i in issues) else MT5AuditEventType.BRIDGE_VALIDATION_FAILED
            self._audit.record(event_type, summary)
        return issues

    # ------------------------------------------------------------------
    # Import (configuration only -- never trade)
    # ------------------------------------------------------------------

    def import_request(self, raw: str) -> ImportResult:
        """Import requests have their own small `{"kind", "params"}`
        shape -- deliberately NOT validated against `bridge_validator`'s
        combined-document schema (that would reject every legal import
        payload for "missing version/timestamp" and "unknown field
        'kind'"). Malformed JSON and everything else illegal about an
        import request is caught by `bridge_import.parse_import` itself,
        which is the actual authority on import-request shape."""
        try:
            payload = deserialize(raw)
        except json.JSONDecodeError as exc:
            issue = f"Malformed JSON: {exc}"
            self._audit.record(MT5AuditEventType.BRIDGE_VALIDATION_FAILED, issue[:200])
            return ImportResult(success=False, issues=[issue], result=None)

        try:
            request: BridgeImportRequest = parse_import(payload)
            result = apply_import(request, self._mt5_manager)
        except BridgeImportError as exc:
            self._audit.record(MT5AuditEventType.BRIDGE_VALIDATION_FAILED, str(exc)[:200])
            return ImportResult(success=False, issues=[str(exc)], result=None)
        except MT5Error as exc:
            return ImportResult(success=False, issues=[str(exc)], result=None)

        with self._lock:
            self._state.import_count += 1
            self._state.last_import_at = datetime.now(timezone.utc)
            self._save_state()
        self._audit.record(MT5AuditEventType.BRIDGE_IMPORTED, request.kind.value)
        return ImportResult(success=True, issues=[], result=result)

    # ------------------------------------------------------------------
    # Health / audit / existing bridge_manager pass-throughs
    # ------------------------------------------------------------------

    def get_health(self) -> BridgeHealth:
        return build_bridge_health(
            bridge_version=BRIDGE_VERSION,
            schema_version=bridge_manager.schema_version(),
            export_count=self._state.export_count,
            import_count=self._state.import_count,
            last_export_at=self._state.last_export_at,
            last_import_at=self._state.last_import_at,
            last_validation_at=self._state.last_validation_at,
            last_validation_ok=self._state.last_validation_ok,
            transport_available=False,  # no real transport exists this phase either -- see ipc.py
            checksum_status="active" if self._state.export_count > 0 else "not yet used",
        )

    def list_recent_audit_events(self, limit: int = 50) -> list:
        all_events = self._audit.list_events(limit=max(limit * 4, 200))
        return [e for e in all_events if e.event_type in _BRIDGE_AUDIT_KINDS][:limit]

    def list_transports(self):
        return bridge_manager.list_transports()

    def schema_version(self) -> str:
        return bridge_manager.schema_version()

    def preview_payload(self) -> dict[str, Any]:
        return bridge_manager.preview_payload()
