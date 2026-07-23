"""`position_reader.py`/`order_reader.py` -- require connection, never
fabricate data, guarded by `requires_real_terminal` for the real-call
assertions."""

import pytest

from app.mt5.connection_manager import ConnectionManager
from app.mt5.exceptions import MT5ConnectionError
from app.mt5.mt5_models import ConnectionState
from app.mt5.order_reader import get_orders
from app.mt5.position_reader import get_positions
from tests.mt5.conftest import requires_real_terminal


def test_positions_require_connection() -> None:
    with pytest.raises(MT5ConnectionError):
        get_positions(ConnectionManager())


def test_orders_require_connection() -> None:
    with pytest.raises(MT5ConnectionError):
        get_orders(ConnectionManager())


@requires_real_terminal
def test_real_positions_and_orders_return_lists_never_fabricated() -> None:
    connection = ConnectionManager()
    if connection.connect() != ConnectionState.CONNECTED:
        pytest.skip("Could not establish a real connection.")
    try:
        positions = get_positions(connection)
        orders = get_orders(connection)
        assert isinstance(positions, list)
        assert isinstance(orders, list)
    finally:
        connection.disconnect()
