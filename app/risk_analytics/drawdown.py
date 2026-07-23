"""Drawdown episode analysis (Phase 17.7). Wraps the already-computed
`DrawdownReport` (`app.backtesting_engine.models`) -- `max_drawdown`/
`max_drawdown_pct`/`average_drawdown` are read straight off it, never
recomputed. The genuinely new piece is per-episode recovery time: bars
from a drawdown's trough back to a new equity high, derived purely from
`DrawdownReport.points` (each point already carries `drawdown_pct`).
"""

from app.backtesting_engine.models import DrawdownReport
from app.risk_analytics.risk_models import DrawdownAnalysis, DrawdownEpisode


def analyze_drawdown(drawdown_report: DrawdownReport) -> DrawdownAnalysis:
    episodes: list[DrawdownEpisode] = []
    points = drawdown_report.points

    in_episode = False
    start_index = trough_index = 0
    trough_pct = 0.0

    for point in points:
        if point.drawdown_pct > 0:
            if not in_episode:
                in_episode = True
                start_index = point.index
                trough_index = point.index
                trough_pct = point.drawdown_pct
            elif point.drawdown_pct > trough_pct:
                trough_index = point.index
                trough_pct = point.drawdown_pct
        else:
            if in_episode:
                episodes.append(
                    DrawdownEpisode(
                        start_index=start_index, trough_index=trough_index, recovery_index=point.index,
                        drawdown_pct=trough_pct, recovery_time_bars=point.index - trough_index,
                    )
                )
                in_episode = False

    if in_episode:
        # Drawdown never recovered by the end of the run -- honestly reported as unrecovered.
        episodes.append(
            DrawdownEpisode(start_index=start_index, trough_index=trough_index, recovery_index=None, drawdown_pct=trough_pct, recovery_time_bars=None)
        )

    recovered = [e.recovery_time_bars for e in episodes if e.recovery_time_bars is not None]
    average_recovery = round(sum(recovered) / len(recovered), 2) if recovered else None

    return DrawdownAnalysis(
        max_drawdown=drawdown_report.max_drawdown,
        max_drawdown_pct=drawdown_report.max_drawdown_pct,
        average_drawdown=drawdown_report.average_drawdown,
        episodes=[
            {
                "start_index": e.start_index, "trough_index": e.trough_index, "recovery_index": e.recovery_index,
                "drawdown_pct": e.drawdown_pct, "recovery_time_bars": e.recovery_time_bars,
            }
            for e in episodes
        ],
        average_recovery_time_bars=average_recovery,
    )
