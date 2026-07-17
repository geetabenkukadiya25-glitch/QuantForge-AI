"""Shared fixtures for tests/ui."""

import pytest


@pytest.fixture
def sample_csv_bytes() -> bytes:
    """A minimal, valid standard-schema OHLCV CSV (9 daily candles)."""
    header = b"Datetime,Open,High,Low,Close,Volume\n"
    rows = b"\n".join(
        f"2024-01-{1 + i:02d} 00:00:00,1.10{i},1.11{i},1.09{i},1.105{i},100".encode() for i in range(9)
    )
    return header + rows
