"""`DrawdownAnalyzer`, `PerformanceAnalyzer`, and `StatisticsEngine`."""

import pytest

from app.backtesting_engine.models import EquityCurve, EquityPoint, ExitReason, Trade, TradeDirection, TradeStatus
from app.backtesting_engine.statistics import DrawdownAnalyzer, PerformanceAnalyzer, StatisticsEngine


def _trade(net: float) -> Trade:
    gross = net + 0.0
    return Trade(
        trade_id=f"T-{net}",
        direction=TradeDirection.BUY,
        entry_index=0,
        entry_datetime="t0",
        entry_price=100.0,
        volume=1.0,
        exit_index=1,
        exit_datetime="t1",
        exit_price=100.0 + net,
        status=TradeStatus.CLOSED,
        exit_reason=ExitReason.SIGNAL,
        gross_profit=gross,
        commission=0.0,
        swap=0.0,
    )


def _equity_curve(values: list[float]) -> EquityCurve:
    return EquityCurve(points=tuple(EquityPoint(index=i, datetime=f"t{i}", equity=v) for i, v in enumerate(values)))


def test_drawdown_analyzer_tracks_peak_to_trough() -> None:
    curve = _equity_curve([100, 110, 90, 95, 120])
    report = DrawdownAnalyzer().analyze(curve)
    assert report.max_drawdown == pytest.approx(20.0)
    assert report.max_drawdown_pct == pytest.approx(20.0 / 110 * 100.0)


def test_drawdown_analyzer_handles_empty_curve() -> None:
    report = DrawdownAnalyzer().analyze(EquityCurve())
    assert report.max_drawdown == 0.0
    assert report.points == ()


def test_performance_analyzer_computes_win_rate_and_profit_factor() -> None:
    trades = [_trade(10.0), _trade(-5.0), _trade(20.0), _trade(-5.0)]
    curve = _equity_curve([10000, 10010, 10005, 10025, 10020])
    drawdown = DrawdownAnalyzer().analyze(curve)
    stats = PerformanceAnalyzer().analyze(trades, curve, drawdown)
    assert stats.total_trades == 4
    assert stats.winning_trades == 2
    assert stats.losing_trades == 2
    assert stats.win_rate == pytest.approx(50.0)
    assert stats.gross_profit == pytest.approx(30.0)
    assert stats.gross_loss == pytest.approx(10.0)
    assert stats.profit_factor == pytest.approx(3.0)
    assert stats.net_profit == pytest.approx(20.0)
    assert stats.expectancy == pytest.approx(5.0)


def test_performance_analyzer_handles_no_trades() -> None:
    curve = _equity_curve([10000, 10000])
    drawdown = DrawdownAnalyzer().analyze(curve)
    stats = PerformanceAnalyzer().analyze([], curve, drawdown)
    assert stats.total_trades == 0
    assert stats.win_rate == 0.0
    assert stats.profit_factor is None


def test_statistics_engine_combines_both_analyzers() -> None:
    trades = [_trade(10.0), _trade(-5.0)]
    curve = _equity_curve([10000, 10010, 10005])
    drawdown, stats = StatisticsEngine().compute(trades, curve)
    assert drawdown.max_drawdown >= 0.0
    assert stats.total_trades == 2
