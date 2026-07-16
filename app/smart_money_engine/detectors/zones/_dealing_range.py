"""Shared dealing-range computation for Premium/Discount/Equilibrium detectors.

Not a detector itself. A "dealing range" is the price range between two
consecutive, alternating swing points (a swing high followed by a swing
low, or vice versa) -- the classic reference range Premium/Discount/
Equilibrium zones are drawn against.
"""

from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs, find_swing_lows


def compute_dealing_ranges(
    context: SMCContext, left_bars: int, right_bars: int
) -> list[tuple[int, float, float]]:
    """Return `(index, top, bottom)` for each range formed by consecutive alternating swings.

    `index` is the later swing's position -- where the range becomes active.
    """
    data = context.data
    highs = [(i, float(data["High"].iloc[i]), "high") for i in find_swing_highs(data, left_bars, right_bars)]
    lows = [(i, float(data["Low"].iloc[i]), "low") for i in find_swing_lows(data, left_bars, right_bars)]
    swings = sorted(highs + lows, key=lambda item: item[0])

    ranges: list[tuple[int, float, float]] = []
    for a, b in zip(swings, swings[1:]):
        if a[2] == b[2]:
            continue
        top, bottom = max(a[1], b[1]), min(a[1], b[1])
        if top > bottom:
            ranges.append((b[0], top, bottom))
    return ranges
