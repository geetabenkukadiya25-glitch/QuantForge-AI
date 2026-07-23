"""`scenario_analysis.py` -- regime classification on synthetic
trending/flat price series, and trade-to-regime matching."""

import numpy as np
import pandas as pd

from app.backtesting_engine.models import Trade, TradeDirection, TradeStatus
from app.risk_analytics.scenario_analysis import analyze_scenario, classify_regimes, custom_scenario


def _trending_df(n: int = 100, drift: float = 0.01) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    close = 100 * np.cumprod(1 + drift + rng.normal(0, 0.0005, n))
    return pd.DataFrame({"Close": close})


def _flat_df(n: int = 100) -> pd.DataFrame:
    rng = np.random.default_rng(2)
    close = 100 + rng.normal(0, 0.01, n)
    return pd.DataFrame({"Close": close})


def _trade(trade_id: str, entry_index: int, net_profit: float) -> Trade:
    return Trade(
        trade_id=trade_id, direction=TradeDirection.BUY, entry_index=entry_index, entry_datetime="2024-01-01T00:00:00",
        entry_price=1.1, volume=1.0, exit_index=entry_index + 1, exit_datetime="2024-01-01T01:00:00",
        exit_price=1.1 + net_profit, status=TradeStatus.CLOSED, gross_profit=net_profit,
    )


def test_classify_regimes_strongly_trending_series_has_bull_segments() -> None:
    segments = classify_regimes(_trending_df(drift=0.02))
    kinds = {s.kind for s in segments}
    assert "BULL" in kinds


def test_classify_regimes_too_short_series_returns_empty() -> None:
    assert classify_regimes(_trending_df(n=5)) == []


def test_classify_regimes_segments_cover_the_whole_series() -> None:
    df = _flat_df()
    segments = classify_regimes(df)
    assert segments[0].start_index == 0
    assert segments[-1].end_index == len(df) - 1
    # Segments are contiguous, non-overlapping.
    for a, b in zip(segments, segments[1:]):
        assert b.start_index == a.end_index + 1


def test_analyze_scenario_matches_trades_within_segments() -> None:
    from app.risk_analytics.risk_models import RegimeSegment

    segments = [RegimeSegment(kind="BULL", start_index=0, end_index=10), RegimeSegment(kind="BEAR", start_index=11, end_index=20)]
    trades = (_trade("t1", 5, 10.0), _trade("t2", 15, -5.0), _trade("t3", 3, 20.0))
    result = analyze_scenario(trades, segments, "BULL")
    assert result.trade_count == 2
    assert result.net_profit == 30.0


def test_custom_scenario_uses_supplied_ranges() -> None:
    trades = (_trade("t1", 5, 10.0), _trade("t2", 50, -5.0))
    result = custom_scenario(trades, ranges=[(0, 10)], label="Event Window")
    assert result.scenario == "Event Window"
    assert result.trade_count == 1
    assert result.net_profit == 10.0
