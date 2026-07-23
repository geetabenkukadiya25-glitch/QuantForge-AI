"""Scenario / market-regime analysis (Phase 17.7) -- confirmed absent
anywhere else in the codebase. Rule-based regime classification over a
dataset's own Close-price series (self-relative thresholds, no
hardcoded global percentages), then performance of the trades whose
entry falls inside each regime segment. Never mutates the input
DataFrame or historical data -- read-only throughout.
"""

import pandas as pd

from app.backtesting_engine.models import Trade
from app.risk_analytics.risk_models import RegimeKind, RegimeSegment, ScenarioResult

_TREND_WINDOW = 20
_VOL_WINDOW = 20


def classify_regimes(df: pd.DataFrame, close_col: str = "Close") -> list[RegimeSegment]:
    """One `RegimeKind` label per candle, then run-length-encoded into
    segments. Volatility is classified first (extreme volatility is
    reported regardless of trend direction); trend then splits the
    remaining calmer candles into Bull/Bear/Sideways."""
    if len(df) < _TREND_WINDOW + 1:
        return []

    close = df[close_col].reset_index(drop=True)
    trend = close.pct_change(_TREND_WINDOW)
    returns = close.pct_change()
    rolling_vol = returns.rolling(_VOL_WINDOW).std()

    vol_valid = rolling_vol.dropna()
    high_vol_threshold = vol_valid.quantile(0.75) if not vol_valid.empty else float("inf")
    low_vol_threshold = vol_valid.quantile(0.25) if not vol_valid.empty else 0.0
    trend_valid = trend.dropna().abs()
    trend_threshold = trend_valid.quantile(0.5) if not trend_valid.empty else 0.0

    labels: list[str] = []
    for i in range(len(close)):
        vol = rolling_vol.iloc[i]
        tr = trend.iloc[i]
        if pd.isna(vol) or pd.isna(tr):
            labels.append(RegimeKind.SIDEWAYS.value)
            continue
        if vol >= high_vol_threshold:
            labels.append(RegimeKind.HIGH_VOLATILITY.value)
        elif vol <= low_vol_threshold:
            labels.append(RegimeKind.LOW_VOLATILITY.value)
        elif tr > trend_threshold:
            labels.append(RegimeKind.BULL.value)
        elif tr < -trend_threshold:
            labels.append(RegimeKind.BEAR.value)
        else:
            labels.append(RegimeKind.SIDEWAYS.value)

    segments: list[RegimeSegment] = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            segments.append(RegimeSegment(kind=labels[start], start_index=start, end_index=i - 1))
            start = i
    return segments


def analyze_scenario(trades: tuple[Trade, ...], segments: list[RegimeSegment], scenario: str) -> ScenarioResult:
    """Performance of every trade whose `entry_index` falls inside a
    segment matching `scenario` (a `RegimeKind` value, or any label for a
    Custom segment list the caller supplied directly)."""
    ranges = [(s.start_index, s.end_index) for s in segments if s.kind == scenario]
    matching = [t for t in trades if t.exit_price is not None and any(lo <= t.entry_index <= hi for lo, hi in ranges)]

    net_profit = sum(t.net_profit for t in matching)
    wins = [t for t in matching if t.net_profit > 0]
    win_rate = round(len(wins) / len(matching), 6) if matching else 0.0
    average_return = round(net_profit / len(matching), 4) if matching else 0.0

    return ScenarioResult(scenario=scenario, trade_count=len(matching), net_profit=round(net_profit, 4), win_rate=win_rate, average_trade_return=average_return)


def custom_scenario(trades: tuple[Trade, ...], ranges: list[tuple[int, int]], label: str = "Custom") -> ScenarioResult:
    """A caller-supplied set of `(start_index, end_index)` candle ranges,
    for a scenario that isn't one of the rule-based regimes (e.g. a
    specific historical event window)."""
    segments = [RegimeSegment(kind=label, start_index=lo, end_index=hi) for lo, hi in ranges]
    return analyze_scenario(trades, segments, label)
