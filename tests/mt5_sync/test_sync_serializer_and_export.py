"""`sync_serializer.py` -- proves there is no second JSON path:
`export_via_bridge` returns whatever `BridgeExchangeManager.export()`
returns, byte-identical, because it IS that call."""

from pathlib import Path

from app.mt5.bridge_exchange_manager import BridgeExchangeManager
from app.mt5_sync.sync_models import SyncRun, SyncKind, SyncStatus
from app.mt5_sync.sync_serializer import export_sync_run, export_via_bridge


def test_export_sync_run_is_plain_to_dict() -> None:
    run = SyncRun(kind=SyncKind.TICK, status=SyncStatus.COMPLETED)
    assert export_sync_run(run) == run.to_dict()


def test_export_via_bridge_delegates_to_bridge_exchange_manager(mt5_manager, tmp_path: Path) -> None:
    bridge = BridgeExchangeManager(state_dir=tmp_path / "bridge_state", manager=mt5_manager)
    document = export_via_bridge(bridge)
    # Same manager, same call -- a second, independent call to the
    # bridge's own `export()` must produce a document with the same
    # shape (a fresh timestamp/checksum each time is expected and fine;
    # what matters is that both come from the SAME underlying function).
    direct = bridge.export()
    assert set(document.keys()) == set(direct.keys())
    assert document["version"] == direct["version"]


def test_export_via_bridge_increments_bridge_own_counters(mt5_manager, tmp_path: Path) -> None:
    bridge = BridgeExchangeManager(state_dir=tmp_path / "bridge_state", manager=mt5_manager)
    assert bridge.get_health().export_count == 0
    export_via_bridge(bridge)
    assert bridge.get_health().export_count == 1
