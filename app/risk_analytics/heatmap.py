"""Time-bucketed performance heatmaps (Phase 17.7) -- confirmed absent
anywhere else in the codebase (`research_engine.AnalyticsEngine` only
buckets by symbol/declared-session/timeframe *across strategies*, never
by a single strategy's own trade timestamps). Every bucketing function
here groups `Trade.entry_datetime`/`net_profit` -- read-only, no
historical data mutation.
"""

from collections import defaultdict

import pandas as pd

from app.backtesting_engine.models import DrawdownReport, Trade
from app.risk_analytics.risk_models import HeatmapResult

# Simple, documented UTC hour-range convention for trading-session
# labeling -- an honest framework approximation, not broker-specific.
_SESSION_HOURS = {"Asian": range(0, 8), "London": range(8, 16), "New York": range(13, 21)}


def _closed_trades_frame(trades: tuple[Trade, ...]) -> pd.DataFrame:
    closed = [t for t in trades if t.exit_price is not None]
    if not closed:
        return pd.DataFrame(columns=["datetime", "net_profit"])
    return pd.DataFrame({"datetime": pd.to_datetime([t.entry_datetime for t in closed]), "net_profit": [t.net_profit for t in closed]})


def _bucket_sum(df: pd.DataFrame, key) -> dict[str, float]:
    if df.empty:
        return {}
    grouped = df.groupby(key)["net_profit"].sum()
    return {str(k): round(float(v), 4) for k, v in grouped.items()}


def monthly_returns(trades: tuple[Trade, ...]) -> HeatmapResult:
    df = _closed_trades_frame(trades)
    buckets = _bucket_sum(df, df["datetime"].dt.strftime("%Y-%m")) if not df.empty else {}
    return HeatmapResult(kind="monthly", buckets=buckets)


def weekly_returns(trades: tuple[Trade, ...]) -> HeatmapResult:
    df = _closed_trades_frame(trades)
    buckets = _bucket_sum(df, df["datetime"].dt.strftime("%G-W%V")) if not df.empty else {}
    return HeatmapResult(kind="weekly", buckets=buckets)


def daily_returns(trades: tuple[Trade, ...]) -> HeatmapResult:
    df = _closed_trades_frame(trades)
    buckets = _bucket_sum(df, df["datetime"].dt.day_name()) if not df.empty else {}
    return HeatmapResult(kind="daily", buckets=buckets)


def hourly_performance(trades: tuple[Trade, ...]) -> HeatmapResult:
    df = _closed_trades_frame(trades)
    buckets = _bucket_sum(df, df["datetime"].dt.hour.map(lambda h: f"{h:02d}:00")) if not df.empty else {}
    return HeatmapResult(kind="hourly", buckets=buckets)


def session_performance(trades: tuple[Trade, ...]) -> HeatmapResult:
    df = _closed_trades_frame(trades)
    if df.empty:
        return HeatmapResult(kind="session", buckets={})
    totals: dict[str, float] = defaultdict(float)
    for _, row in df.iterrows():
        hour = row["datetime"].hour
        for session, hours in _SESSION_HOURS.items():
            if hour in hours:
                totals[session] += row["net_profit"]
    return HeatmapResult(kind="session", buckets={k: round(v, 4) for k, v in totals.items()})


def drawdown_heatmap(drawdown_report: DrawdownReport) -> HeatmapResult:
    """Max drawdown_pct observed per calendar month, from
    `DrawdownReport.points` (already computed -- never re-derived)."""
    if not drawdown_report.points:
        return HeatmapResult(kind="drawdown", buckets={})
    df = pd.DataFrame({"datetime": pd.to_datetime([p.datetime for p in drawdown_report.points]), "drawdown_pct": [p.drawdown_pct for p in drawdown_report.points]})
    grouped = df.groupby(df["datetime"].dt.strftime("%Y-%m"))["drawdown_pct"].max()
    return HeatmapResult(kind="drawdown", buckets={str(k): round(float(v), 4) for k, v in grouped.items()})


def risk_heatmap(trades: tuple[Trade, ...]) -> HeatmapResult:
    """Per-month composite risk indicator: share of losing trades that
    month times average loss magnitude -- a simple, transparent
    framework proxy, not a re-derivation of any existing risk score."""
    closed = [t for t in trades if t.exit_price is not None]
    if not closed:
        return HeatmapResult(kind="risk", buckets={})
    df = pd.DataFrame({
        "datetime": pd.to_datetime([t.entry_datetime for t in closed]),
        "net_profit": [t.net_profit for t in closed],
        "is_loss": [t.net_profit <= 0 for t in closed],
    })
    buckets: dict[str, float] = {}
    for month, group in df.groupby(df["datetime"].dt.strftime("%Y-%m")):
        losses = group[group["is_loss"]]["net_profit"]
        loss_rate = len(losses) / len(group)
        avg_loss_magnitude = abs(losses.mean()) if not losses.empty else 0.0
        buckets[str(month)] = round(loss_rate * avg_loss_magnitude, 4)
    return HeatmapResult(kind="risk", buckets=buckets)
