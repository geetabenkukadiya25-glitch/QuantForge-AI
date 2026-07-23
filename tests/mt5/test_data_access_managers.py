"""`account_manager.py`/`symbol_manager.py`/`market_watch.py`/
`history_manager.py`/`tick_manager.py`/`terminal_information.py` --
every one of these wrappers must raise (never return fabricated data)
when not connected, and every real call is guarded by
`requires_real_terminal` so the suite passes identically with or
without a live terminal."""

from datetime import datetime, timedelta

import pytest

from app.mt5.account_manager import get_account_info
from app.mt5.connection_manager import ConnectionManager
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.history_manager import copy_rates_range
from app.mt5.market_watch import get_market_depth, get_quote
from app.mt5.mt5_models import ConnectionState
from app.mt5.symbol_manager import get_symbol_info, list_symbols
from app.mt5.terminal_information import get_terminal_info
from app.mt5.tick_manager import copy_ticks_range
from tests.mt5.conftest import requires_real_terminal


@pytest.fixture
def disconnected() -> ConnectionManager:
    return ConnectionManager()


def test_account_info_requires_connection(disconnected) -> None:
    with pytest.raises(MT5ConnectionError):
        get_account_info(disconnected)


def test_terminal_info_requires_connection(disconnected) -> None:
    with pytest.raises(MT5ConnectionError):
        get_terminal_info(disconnected)


def test_symbols_require_connection(disconnected) -> None:
    with pytest.raises(MT5ConnectionError):
        list_symbols(disconnected)
    with pytest.raises(MT5ConnectionError):
        get_symbol_info(disconnected, "EURUSD")


def test_quote_and_depth_require_connection(disconnected) -> None:
    with pytest.raises(MT5ConnectionError):
        get_quote(disconnected, "EURUSD")
    with pytest.raises(MT5ConnectionError):
        get_market_depth(disconnected, "EURUSD")


def test_history_and_ticks_require_connection(disconnected) -> None:
    now = datetime.now()
    with pytest.raises(MT5ConnectionError):
        copy_rates_range(disconnected, "EURUSD", "H1", now - timedelta(days=1), now)
    with pytest.raises(MT5ConnectionError):
        copy_ticks_range(disconnected, "EURUSD", now - timedelta(minutes=5), now)


@pytest.fixture
def connected():
    manager = ConnectionManager()
    if manager.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    yield manager
    manager.disconnect()


@requires_real_terminal
def test_real_account_info_never_fabricated(connected) -> None:
    info = get_account_info(connected)
    assert info.login > 0
    assert isinstance(info.currency, str) and info.currency


@requires_real_terminal
def test_real_terminal_info_reports_connected_true(connected) -> None:
    info = get_terminal_info(connected)
    assert info.connected is True
    assert info.build > 0


@requires_real_terminal
def test_real_symbols_nonempty(connected) -> None:
    symbols = list_symbols(connected)
    assert len(symbols) > 0
    first = get_symbol_info(connected, symbols[0].name)
    assert first.name == symbols[0].name


@requires_real_terminal
def test_real_quote_for_a_visible_symbol(connected) -> None:
    symbols = [s for s in list_symbols(connected) if s.visible]
    if not symbols:
        pytest.skip("No visible symbols on this terminal's Market Watch.")
    quote = get_quote(connected, symbols[0].name)
    assert quote.symbol == symbols[0].name


@requires_real_terminal
def test_real_history_returns_bars_or_empty_never_raises_unexpectedly(connected) -> None:
    symbols = [s for s in list_symbols(connected) if s.visible]
    if not symbols:
        pytest.skip("No visible symbols on this terminal's Market Watch.")
    now = datetime.now()
    bars = copy_rates_range(connected, symbols[0].name, "H1", now - timedelta(days=3), now)
    assert isinstance(bars, list)
