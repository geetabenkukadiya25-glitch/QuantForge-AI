"""`ReplayCursor`: forward, backward, jump-to-candle, jump-to-time, beginning/end navigation."""

import pytest

from app.replay_engine.cursor import ReplayCursor
from app.replay_engine.exceptions import ReplayNavigationError
from app.replay_engine.models import ReplayTimeline


@pytest.fixture
def timeline() -> ReplayTimeline:
    return ReplayTimeline(
        symbol="EURUSD", timeframe="H1", total_frames=5, start_index=0, end_index=4,
        frame_datetimes=("t0", "t1", "t2", "t3", "t4"),
    )


def test_starts_at_the_beginning(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    assert cursor.index == 0
    assert cursor.at_beginning
    assert not cursor.at_end


def test_forward_advances_and_clamps_at_the_end(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    assert cursor.forward(2) == 2
    assert cursor.forward(10) == 4
    assert cursor.at_end


def test_backward_rewinds_and_clamps_at_the_beginning(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    cursor.jump_to_candle(3)
    assert cursor.backward(1) == 2
    assert cursor.backward(10) == 0
    assert cursor.at_beginning


def test_jump_to_candle_out_of_range_raises(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    with pytest.raises(ReplayNavigationError):
        cursor.jump_to_candle(99)
    with pytest.raises(ReplayNavigationError):
        cursor.jump_to_candle(-1)


def test_jump_to_time_moves_to_the_matching_frame(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    assert cursor.jump_to_time("t3") == 3
    assert cursor.datetime == "t3"


def test_jump_to_unknown_time_raises(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    with pytest.raises(ReplayNavigationError):
        cursor.jump_to_time("does-not-exist")


def test_go_to_beginning_and_end(timeline: ReplayTimeline) -> None:
    cursor = ReplayCursor(timeline=timeline)
    cursor.jump_to_candle(2)
    assert cursor.go_to_end() == 4
    assert cursor.go_to_beginning() == 0


def test_empty_timeline_cannot_be_navigated() -> None:
    empty = ReplayTimeline(symbol="EURUSD", timeframe="H1", total_frames=0, start_index=0, end_index=0)
    with pytest.raises(ReplayNavigationError):
        ReplayCursor(timeline=empty)
