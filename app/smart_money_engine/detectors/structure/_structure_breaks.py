"""Shared BOS/CHoCH scan logic.

Not a detector itself -- `BOSDetector` and `CHoCHDetector` both call
`scan_structure_breaks` and filter its output, so the trend-tracking
state machine exists in exactly one place.

Algorithm (a standard, simplified public formulation of SMC structure
breaks): track the most recent confirmed swing high/low. When price
closes beyond one of them, that is a "break" -- if the break continues
the already-established trend, label it BOS (continuation); if it
reverses the established trend, label it CHoCH (change of character).
"""

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows
from app.smart_money_engine.result import SMCDetection
from app.smart_money_engine.schema import DATETIME_COL


def scan_structure_breaks(context: SMCContext, left_bars: int, right_bars: int) -> list[SMCDetection]:
    data = context.data
    highs = {i: float(data["High"].iloc[i]) for i in find_swing_highs(data, left_bars, right_bars)}
    lows = {i: float(data["Low"].iloc[i]) for i in find_swing_lows(data, left_bars, right_bars)}
    close = data["Close"]

    swing_events = sorted(
        [(i, "high") for i in highs] + [(i, "low") for i in lows], key=lambda item: item[0]
    )

    detections: list[SMCDetection] = []
    trend: str | None = None
    active_high: float | None = None
    active_low: float | None = None
    broken_high_indices: set[int] = set()
    broken_low_indices: set[int] = set()

    swing_pointer = 0
    for candle_index in range(len(data)):
        while swing_pointer < len(swing_events) and swing_events[swing_pointer][0] <= candle_index:
            idx, kind = swing_events[swing_pointer]
            if kind == "high":
                active_high = highs[idx]
            else:
                active_low = lows[idx]
            swing_pointer += 1

        price = float(close.iloc[candle_index])

        if active_high is not None and price > active_high and candle_index not in broken_high_indices:
            if trend == "bearish":
                label, direction = "Bullish CHoCH", "bullish"
            else:
                label, direction = "Bullish BOS", "bullish"
            detections.append(
                SMCDetection(
                    index=candle_index,
                    datetime=_iso(data, candle_index),
                    label=label,
                    direction=direction,
                    price=active_high,
                    notes="Break of the most recent swing high.",
                )
            )
            trend = "bullish"
            broken_high_indices.add(candle_index)
            active_high = None

        if active_low is not None and price < active_low and candle_index not in broken_low_indices:
            if trend == "bullish":
                label, direction = "Bearish CHoCH", "bearish"
            else:
                label, direction = "Bearish BOS", "bearish"
            detections.append(
                SMCDetection(
                    index=candle_index,
                    datetime=_iso(data, candle_index),
                    label=label,
                    direction=direction,
                    price=active_low,
                    notes="Break of the most recent swing low.",
                )
            )
            trend = "bearish"
            broken_low_indices.add(candle_index)
            active_low = None

    return detections


def _iso(data, index: int) -> str:
    value = data[DATETIME_COL].iloc[index]
    return value.isoformat() if hasattr(value, "isoformat") else str(value)
