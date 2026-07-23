"""`heatmap.py` -- time-bucketed performance, genuinely new bucketing
logic verified against a known trade-timestamp distribution."""

from app.backtesting_engine.models import DrawdownPoint, DrawdownReport, Trade, TradeDirection, TradeStatus
from app.risk_analytics.heatmap import daily_returns, drawdown_heatmap, hourly_performance, monthly_returns


def _trade(trade_id: str, entry_datetime: str, net_profit: float) -> Trade:
    return Trade(
        trade_id=trade_id, direction=TradeDirection.BUY, entry_index=0, entry_datetime=entry_datetime,
        entry_price=1.1, volume=1.0, exit_index=1, exit_datetime=entry_datetime,
        exit_price=1.1 + net_profit, status=TradeStatus.CLOSED, gross_profit=net_profit,
    )


def test_monthly_returns_buckets_by_calendar_month() -> None:
    trades = (_trade("t1", "2024-01-05T10:00:00", 10.0), _trade("t2", "2024-01-20T10:00:00", 5.0), _trade("t3", "2024-02-01T10:00:00", -20.0))
    result = monthly_returns(trades)
    assert result.buckets == {"2024-01": 15.0, "2024-02": -20.0}


def test_hourly_performance_buckets_by_hour() -> None:
    trades = (_trade("t1", "2024-01-05T09:00:00", 10.0), _trade("t2", "2024-01-06T09:00:00", 5.0), _trade("t3", "2024-01-07T14:00:00", -3.0))
    result = hourly_performance(trades)
    assert result.buckets["09:00"] == 15.0
    assert result.buckets["14:00"] == -3.0


def test_daily_returns_buckets_by_weekday() -> None:
    # 2024-01-01 is a Monday.
    trades = (_trade("t1", "2024-01-01T10:00:00", 10.0), _trade("t2", "2024-01-08T10:00:00", 5.0))
    result = daily_returns(trades)
    assert result.buckets["Monday"] == 15.0


def test_heatmap_empty_trades_returns_empty_buckets() -> None:
    assert monthly_returns(()).buckets == {}


def test_drawdown_heatmap_max_per_month() -> None:
    points = (
        DrawdownPoint(index=0, datetime="2024-01-05T00:00:00", drawdown=10, drawdown_pct=5.0),
        DrawdownPoint(index=1, datetime="2024-01-10T00:00:00", drawdown=20, drawdown_pct=8.0),
        DrawdownPoint(index=2, datetime="2024-02-01T00:00:00", drawdown=5, drawdown_pct=2.0),
    )
    report = DrawdownReport(points=points, max_drawdown=20, max_drawdown_pct=8.0, average_drawdown=5.0)
    result = drawdown_heatmap(report)
    assert result.buckets == {"2024-01": 8.0, "2024-02": 2.0}
