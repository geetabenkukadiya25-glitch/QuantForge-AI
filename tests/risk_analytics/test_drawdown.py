"""`drawdown.py` -- episode/recovery-time derivation over an
already-computed `DrawdownReport` (max/avg drawdown read directly,
never recomputed)."""

from app.backtesting_engine.models import DrawdownPoint, DrawdownReport
from app.risk_analytics.drawdown import analyze_drawdown


def _point(index: int, drawdown_pct: float) -> DrawdownPoint:
    return DrawdownPoint(index=index, datetime=f"2024-01-01T{index:02d}:00:00", drawdown=drawdown_pct * 10, drawdown_pct=drawdown_pct)


def test_analyze_drawdown_reads_report_fields_directly() -> None:
    report = DrawdownReport(points=(), max_drawdown=123.0, max_drawdown_pct=45.0, average_drawdown=12.0)
    analysis = analyze_drawdown(report)
    assert analysis.max_drawdown == 123.0
    assert analysis.max_drawdown_pct == 45.0
    assert analysis.average_drawdown == 12.0


def test_analyze_drawdown_finds_recovered_episode() -> None:
    points = [_point(0, 0), _point(1, 5), _point(2, 10), _point(3, 5), _point(4, 0)]
    report = DrawdownReport(points=tuple(points), max_drawdown=10, max_drawdown_pct=10, average_drawdown=5)
    analysis = analyze_drawdown(report)
    assert len(analysis.episodes) == 1
    episode = analysis.episodes[0]
    assert episode["trough_index"] == 2
    assert episode["recovery_index"] == 4
    assert episode["recovery_time_bars"] == 2
    assert analysis.average_recovery_time_bars == 2


def test_analyze_drawdown_flags_unrecovered_episode() -> None:
    points = [_point(0, 0), _point(1, 8), _point(2, 15)]  # never returns to 0
    report = DrawdownReport(points=tuple(points), max_drawdown=15, max_drawdown_pct=15, average_drawdown=8)
    analysis = analyze_drawdown(report)
    assert len(analysis.episodes) == 1
    assert analysis.episodes[0]["recovery_index"] is None
    assert analysis.episodes[0]["recovery_time_bars"] is None
    assert analysis.average_recovery_time_bars is None


def test_analyze_drawdown_multiple_episodes() -> None:
    points = [_point(0, 0), _point(1, 5), _point(2, 0), _point(3, 3), _point(4, 0)]
    report = DrawdownReport(points=tuple(points), max_drawdown=5, max_drawdown_pct=5, average_drawdown=2)
    analysis = analyze_drawdown(report)
    assert len(analysis.episodes) == 2
