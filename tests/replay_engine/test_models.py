"""Frozen/immutable, hashable, versioned model behavior for replay_engine models."""

import pytest
from pydantic import ValidationError

from app.replay_engine.metadata import REPLAY_RESULT_VERSION, ReplayMetadata
from app.replay_engine.models import (
    PlaybackState,
    ReplayConfiguration,
    ReplayEvent,
    ReplayEventType,
    ReplayFrame,
    ReplaySpeed,
    ReplayStatistics,
    ReplayTimeline,
)


def test_replay_configuration_is_frozen_and_hashable() -> None:
    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1")
    with pytest.raises(ValidationError):
        config.symbol = "GBPUSD"
    hash(config)  # must not raise


def test_replay_configuration_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ReplayConfiguration(symbol="EURUSD", timeframe="H1", bogus_field=True)


def test_replay_configuration_defaults() -> None:
    config = ReplayConfiguration(symbol="EURUSD", timeframe="H1")
    assert config.default_speed == ReplaySpeed.X1
    assert config.start_index == 0
    assert config.end_index is None
    assert config.include_indicators is True
    assert config.include_smart_money is True
    assert config.include_backtest_results is True


def test_replay_timeline_is_frozen_and_hashable() -> None:
    timeline = ReplayTimeline(symbol="EURUSD", timeframe="H1", total_frames=3, start_index=0, end_index=2, frame_datetimes=("t0", "t1", "t2"))
    with pytest.raises(ValidationError):
        timeline.total_frames = 5
    hash(timeline)


def test_replay_frame_is_frozen_and_hashable() -> None:
    frame = ReplayFrame(index=0, datetime="t0", open=1.0, high=1.1, low=0.9, close=1.05)
    with pytest.raises(ValidationError):
        frame.close = 2.0
    hash(frame)


def test_replay_event_carries_type_index_datetime() -> None:
    event = ReplayEvent(event_type=ReplayEventType.FRAME_CHANGED, frame_index=3, datetime="t3", message="Advanced.")
    assert event.event_type == ReplayEventType.FRAME_CHANGED
    assert event.frame_index == 3
    hash(event)


def test_replay_metadata_default_version() -> None:
    metadata = ReplayMetadata(replay_id="r1", data_checksum="abc")
    assert metadata.result_version == REPLAY_RESULT_VERSION


def test_replay_statistics_defaults() -> None:
    stats = ReplayStatistics(total_frames=10, symbol="EURUSD", timeframe="H1", start_datetime="t0", end_datetime="t9")
    assert stats.total_trade_markers == 0
    assert stats.total_smart_money_detections == 0
    assert stats.indicators_included == ()


def test_playback_state_values() -> None:
    assert {s.value for s in PlaybackState} == {"STOPPED", "PLAYING", "PAUSED", "FINISHED"}


def test_replay_speed_supports_required_multipliers() -> None:
    supported = {0.25, 0.5, 1.0, 2.0, 4.0, 8.0}
    assert {s.value for s in ReplaySpeed if s != ReplaySpeed.MAXIMUM} == supported
    assert ReplaySpeed.MAXIMUM in ReplaySpeed
