"""Thin serialization adapter (Phase 19.2). This is the ONE place
`app.mt5_sync` touches JSON production, and it does so entirely by
calling through to the EXISTING `BridgeExchangeManager`/
`app.mt5.bridge_serializer` -- "Never bypass the JSON Bridge." Routing
through the actual `BridgeExchangeManager` singleton (not just its
underlying `bridge_export.export_document` function) means the bridge's
own export counters/audit trail correctly reflect every export
regardless of what triggered it -- "Reuse Bridge" means reusing the
manager, not just borrowing its logic. Nothing in this package calls
`json.dumps` on synchronized data directly.
"""

from typing import Any

from app.mt5.bridge_serializer import checksum, deserialize, pretty_json, schema_version, serialize
from app.mt5_sync.sync_models import SyncRun


def export_sync_run(run: SyncRun) -> dict[str, Any]:
    """Bookkeeping-only export of a single `SyncRun` -- a plain
    `to_dict()` call, not a bridge document. `export_via_bridge` below
    is the function that produces an actual bridge document."""
    return run.to_dict()


def export_via_bridge(
    bridge_manager,
    include: set[str] | None = None,
    history_symbol: str | None = None,
    history_timeframe: str = "H1",
    history_count: int = 100,
    tick_symbol: str | None = None,
    tick_count: int = 100,
) -> dict[str, Any]:
    """Calls `BridgeExchangeManager.export(...)` -- the same method the
    Phase 19.1 UI's Export tab calls -- so this is provably not a
    second JSON path: it's the bridge itself, invoked from a different
    caller."""
    return bridge_manager.export(
        include=include,
        history_symbol=history_symbol,
        history_timeframe=history_timeframe,
        history_count=history_count,
        tick_symbol=tick_symbol,
        tick_count=tick_count,
    )


# Re-exported for convenience so callers in `app.mt5_sync` never need to
# import `app.mt5.bridge_serializer` directly -- one seam, one place.
__all__ = ["export_sync_run", "export_via_bridge", "serialize", "deserialize", "checksum", "pretty_json", "schema_version"]
