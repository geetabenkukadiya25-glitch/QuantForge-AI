"""`build_timeline`: deterministic frame ordering over a `ReplayContext`'s configured scope."""

import pandas as pd

from app.replay_engine.context import ReplayContext
from app.replay_engine.models import ReplayConfiguration
from app.replay_engine.timeline import build_timeline


def test_full_range_covers_every_candle(bare_replay_context) -> None:
    timeline = build_timeline(bare_replay_context)
    assert timeline.total_frames == len(bare_replay_context.data)
    assert timeline.start_index == 0
    assert timeline.end_index == len(bare_replay_context.data) - 1


def test_scoped_range_covers_only_the_configured_slice(ohlcv_data: pd.DataFrame) -> None:
    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1", start_index=10, end_index=20)
    context = ReplayContext(data=ohlcv_data, configuration=config)
    timeline = build_timeline(context)
    assert timeline.total_frames == 11
    assert timeline.start_index == 10
    assert timeline.end_index == 20


def test_frame_datetimes_match_source_data_order(bare_replay_context) -> None:
    timeline = build_timeline(bare_replay_context)
    expected = tuple(str(v) for v in bare_replay_context.data["Datetime"])
    assert timeline.frame_datetimes == expected


def test_start_and_end_datetime_bracket_the_timeline(bare_replay_context) -> None:
    timeline = build_timeline(bare_replay_context)
    assert timeline.start_datetime == timeline.frame_datetimes[0]
    assert timeline.end_datetime == timeline.frame_datetimes[-1]


def test_deterministic_given_same_context(bare_replay_context) -> None:
    assert build_timeline(bare_replay_context) == build_timeline(bare_replay_context)
