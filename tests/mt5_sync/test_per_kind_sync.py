"""`symbol_sync.py`/`tick_sync.py`/`bar_sync.py`/`market_watch_sync.py`/
`market_book_sync.py` -- each never raises for a disconnected/failed
read; reports `FAILED` via `SyncRun` instead. Real-terminal assertions
guarded by `requires_real_terminal`."""

import pytest

from app.mt5.mt5_models import ConnectionState
from app.mt5_sync.bar_sync import sync_bars
from app.mt5_sync.exceptions import SyncTargetError
from app.mt5_sync.market_book_sync import sync_market_book
from app.mt5_sync.market_watch_sync import sync_market_watch
from app.mt5_sync.sync_models import SyncKind, SyncStatus
from app.mt5_sync.symbol_sync import sync_symbols
from app.mt5_sync.tick_sync import sync_ticks
from tests.mt5_sync.conftest import requires_real_terminal


def test_symbol_sync_disconnected_reports_failed(mt5_manager) -> None:
    run = sync_symbols(mt5_manager)
    assert run.kind == SyncKind.SYMBOL
    assert run.status == SyncStatus.FAILED
    assert run.error


def test_tick_sync_disconnected_reports_failed(mt5_manager) -> None:
    run = sync_ticks(mt5_manager, "EURUSD", 10)
    assert run.status == SyncStatus.FAILED


def test_bar_sync_disconnected_reports_failed(mt5_manager) -> None:
    run = sync_bars(mt5_manager, "EURUSD", "H1", 10)
    assert run.status == SyncStatus.FAILED


def test_market_watch_sync_disconnected_all_fail(mt5_manager) -> None:
    run = sync_market_watch(mt5_manager, ["EURUSD", "GBPUSD"])
    assert run.status == SyncStatus.FAILED
    assert run.records_synced == 0


def test_market_watch_sync_requires_at_least_one_symbol(mt5_manager) -> None:
    with pytest.raises(SyncTargetError):
        sync_market_watch(mt5_manager, [])


def test_market_book_sync_disconnected_reports_failed(mt5_manager) -> None:
    run = sync_market_book(mt5_manager, "EURUSD")
    assert run.status == SyncStatus.FAILED


@requires_real_terminal
def test_real_symbol_sync(mt5_manager) -> None:
    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        run = sync_symbols(mt5_manager)
        assert run.status == SyncStatus.COMPLETED
        assert run.records_synced > 0
        assert run.latency_ms is not None
    finally:
        mt5_manager.disconnect()


@requires_real_terminal
def test_real_tick_and_bar_sync(mt5_manager) -> None:
    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        symbols = [s for s in mt5_manager.list_symbols() if s.visible]
        if not symbols:
            pytest.skip("No visible symbols on this terminal's Market Watch.")
        symbol = symbols[0].name

        tick_run = sync_ticks(mt5_manager, symbol, 10)
        assert tick_run.status == SyncStatus.COMPLETED

        bar_run = sync_bars(mt5_manager, symbol, "H1", 10)
        assert bar_run.status == SyncStatus.COMPLETED
        assert bar_run.records_synced > 0

        watch_run = sync_market_watch(mt5_manager, [symbol])
        assert watch_run.status == SyncStatus.COMPLETED
        assert watch_run.records_synced == 1

        book_run = sync_market_book(mt5_manager, symbol)
        assert book_run.status == SyncStatus.COMPLETED  # empty book is still COMPLETED, not FAILED
    finally:
        mt5_manager.disconnect()
