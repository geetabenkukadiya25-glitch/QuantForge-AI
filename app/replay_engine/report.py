"""A queryable, presentation-oriented view over a completed `ReplayResult`.

`ReplayReport` never mutates the result or re-runs anything -- it only
presents it (e.g. as `pandas.DataFrame`s for the Streamlit Timeline/Frame/
Trade viewers), mirroring `app.validation_engine.report.ValidationReport`'s
role.
"""

import pandas as pd

from app.replay_engine.models import ReplayResult


class ReplayReport:
    """Read-only, queryable wrapper around one `ReplayResult`."""

    def __init__(self, result: ReplayResult) -> None:
        self._result = result

    @property
    def result(self) -> ReplayResult:
        return self._result

    def timeline_report(self) -> pd.DataFrame:
        """One row per frame index: its datetime."""
        timeline = self._result.timeline
        return pd.DataFrame({"frame_index": range(timeline.total_frames), "datetime": timeline.frame_datetimes})

    def events_report(self) -> pd.DataFrame:
        """One row per recorded `ReplayEvent`."""
        return pd.DataFrame(
            [{"event_type": e.event_type.value, "frame_index": e.frame_index, "datetime": e.datetime, "message": e.message} for e in self._result.events]
        )

    def replay_summary(self) -> dict:
        """A single flat dict combining the top-level identity/statistics -- the "at a glance" summary."""
        stats = self._result.statistics
        return {
            "symbol": stats.symbol,
            "timeframe": stats.timeframe,
            "total_frames": stats.total_frames,
            "start_datetime": stats.start_datetime,
            "end_datetime": stats.end_datetime,
            "total_trade_markers": stats.total_trade_markers,
            "total_smart_money_detections": stats.total_smart_money_detections,
            "indicators_included": stats.indicators_included,
            "smart_money_included": stats.smart_money_included,
            "strategy_id": self._result.metadata.strategy_id,
            "backtest_result_id": self._result.metadata.backtest_result_id,
            "checksum": self._result.checksum,
        }
