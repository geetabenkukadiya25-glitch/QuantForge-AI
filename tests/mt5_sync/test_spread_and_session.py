"""`spread_monitor.py`/`session_sync.py` -- pure computation + ring
buffer, real-terminal spread sampling guarded."""

from datetime import datetime, timezone

import pytest

from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import ConnectionState
from app.mt5_sync.session_sync import compute_sessions
from app.mt5_sync.sync_models import SpreadSample
from app.mt5_sync.spread_monitor import SpreadHistory, sample_spread
from tests.mt5_sync.conftest import requires_real_terminal


def test_sample_spread_disconnected_raises(mt5_manager) -> None:
    with pytest.raises(MT5ConnectionError):
        sample_spread(mt5_manager, "EURUSD")


def test_compute_sessions_returns_four_windows() -> None:
    windows = compute_sessions(datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc))
    assert {w.name for w in windows} == {"Sydney", "Tokyo", "London", "New York"}


def test_compute_sessions_london_active_at_10_utc() -> None:
    windows = {w.name: w for w in compute_sessions(datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc))}
    assert windows["London"].is_active is True
    assert windows["Tokyo"].is_active is False


def test_compute_sessions_sydney_active_across_midnight_wrap() -> None:
    windows = {w.name: w for w in compute_sessions(datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc))}
    assert windows["Sydney"].is_active is True
    windows_early = {w.name: w for w in compute_sessions(datetime(2026, 1, 1, 3, 0, tzinfo=timezone.utc))}
    assert windows_early["Sydney"].is_active is True


def test_compute_sessions_defaults_to_now() -> None:
    windows = compute_sessions()
    assert len(windows) == 4


def test_spread_history_ring_buffer_caps_size() -> None:
    history = SpreadHistory(max_samples=3)
    for i in range(5):
        history.record(SpreadSample(symbol="EURUSD", spread=0.0001 * i, bid=1.0, ask=1.0001, sampled_at=datetime.now()))
    recent = history.recent("EURUSD", limit=10)
    assert len(recent) == 3
    assert recent[-1].spread == 0.0001 * 4  # most recent kept


def test_spread_history_unknown_symbol_returns_empty() -> None:
    history = SpreadHistory()
    assert history.recent("NOPE") == []
    assert history.symbols() == []


@requires_real_terminal
def test_real_spread_sample(mt5_manager) -> None:
    if mt5_manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        symbols = [s for s in mt5_manager.list_symbols() if s.visible]
        if not symbols:
            pytest.skip("No visible symbols on this terminal's Market Watch.")
        sample = sample_spread(mt5_manager, symbols[0].name)
        assert sample.spread >= 0
    finally:
        mt5_manager.disconnect()
