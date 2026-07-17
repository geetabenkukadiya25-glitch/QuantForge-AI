"""`ReplayReport`: read-only, queryable presentation over a `ReplayResult`."""

from app.replay_engine.report import ReplayReport
from app.replay_engine.runner import ReplayRunner


def test_timeline_report_has_one_row_per_frame(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    report = ReplayReport(result)
    df = report.timeline_report()
    assert len(df) == result.timeline.total_frames
    assert list(df.columns) == ["frame_index", "datetime"]


def test_events_report_is_empty_for_a_freshly_prepared_result(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    report = ReplayReport(result)
    df = report.events_report()
    assert len(df) == len(result.events)


def test_replay_summary_matches_result_fields(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    summary = ReplayReport(result).replay_summary()
    assert summary["symbol"] == result.statistics.symbol
    assert summary["total_frames"] == result.statistics.total_frames
    assert summary["checksum"] == result.checksum
    assert summary["strategy_id"] == result.metadata.strategy_id
