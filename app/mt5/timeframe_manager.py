"""Maps the platform's own timeframe vocabulary to
`MetaTrader5.TIMEFRAME_*` constants (Phase 19.0). Pure lookup table, no
I/O -- values match `MetaTrader5/__init__.py`'s constants exactly.
"""

_TIMEFRAME_VALUES: dict[str, int] = {
    "M1": 1,
    "M2": 2,
    "M3": 3,
    "M4": 4,
    "M5": 5,
    "M6": 6,
    "M10": 10,
    "M12": 12,
    "M15": 15,
    "M20": 20,
    "M30": 30,
    "H1": 1 | 0x4000,
    "H2": 2 | 0x4000,
    "H3": 3 | 0x4000,
    "H4": 4 | 0x4000,
    "H6": 6 | 0x4000,
    "H8": 8 | 0x4000,
    "H12": 12 | 0x4000,
    "D1": 24 | 0x4000,
    "W1": 1 | 0x8000,
    "MN1": 1 | 0xC000,
}


def to_mt5_timeframe(name: str) -> int:
    key = name.strip().upper()
    if key not in _TIMEFRAME_VALUES:
        raise ValueError(f"Unknown timeframe '{name}'. Supported: {', '.join(_TIMEFRAME_VALUES)}.")
    return _TIMEFRAME_VALUES[key]


def supported_timeframes() -> list[str]:
    return list(_TIMEFRAME_VALUES.keys())
