"""`ReplayPlayer`: play/pause/resume/stop/restart/step/speed state machine."""

import pytest

from app.replay_engine.cursor import ReplayCursor
from app.replay_engine.exceptions import ReplayNavigationError
from app.replay_engine.models import PlaybackState, ReplayEventType, ReplaySpeed, ReplayTimeline
from app.replay_engine.player import ReplayPlayer


@pytest.fixture
def timeline() -> ReplayTimeline:
    return ReplayTimeline(
        symbol="EURUSD", timeframe="H1", total_frames=5, start_index=0, end_index=4,
        frame_datetimes=("t0", "t1", "t2", "t3", "t4"),
    )


@pytest.fixture
def player(timeline: ReplayTimeline) -> ReplayPlayer:
    return ReplayPlayer(cursor=ReplayCursor(timeline=timeline))


def test_play_transitions_to_playing_and_emits_started(player: ReplayPlayer) -> None:
    player.play()
    assert player.state == PlaybackState.PLAYING
    assert player.events[-1].event_type == ReplayEventType.REPLAY_STARTED


def test_pause_requires_playing(player: ReplayPlayer) -> None:
    with pytest.raises(ReplayNavigationError):
        player.pause()
    player.play()
    player.pause()
    assert player.state == PlaybackState.PAUSED
    assert player.events[-1].event_type == ReplayEventType.REPLAY_PAUSED


def test_resume_requires_paused(player: ReplayPlayer) -> None:
    with pytest.raises(ReplayNavigationError):
        player.resume()
    player.play()
    player.pause()
    player.resume()
    assert player.state == PlaybackState.PLAYING
    assert player.events[-1].event_type == ReplayEventType.REPLAY_RESUMED


def test_stop_resets_cursor_to_beginning(player: ReplayPlayer) -> None:
    player.play()
    player.step_forward(3)
    player.stop()
    assert player.state == PlaybackState.STOPPED
    assert player.cursor.at_beginning


def test_restart_clears_events_and_resets_cursor(player: ReplayPlayer) -> None:
    player.play()
    player.step_forward(2)
    player.restart()
    assert player.events == []
    assert player.cursor.at_beginning
    assert player.state == PlaybackState.STOPPED


def test_step_forward_and_backward(player: ReplayPlayer) -> None:
    assert player.step_forward(2) == 2
    assert player.step_backward(1) == 1


def test_auto_play_tick_advances_by_speed(player: ReplayPlayer) -> None:
    player.set_speed(ReplaySpeed.X2)
    player.play()
    index = player.auto_play_tick()
    assert index == 2


def test_auto_play_tick_maximum_speed_jumps_to_end(player: ReplayPlayer) -> None:
    player.set_speed(ReplaySpeed.MAXIMUM)
    player.play()
    index = player.auto_play_tick()
    assert index == 4
    assert player.state == PlaybackState.FINISHED


def test_auto_play_tick_is_noop_when_not_playing(player: ReplayPlayer) -> None:
    assert player.auto_play_tick() == 0


def test_playing_to_the_end_emits_finished_event(player: ReplayPlayer) -> None:
    player.set_speed(ReplaySpeed.MAXIMUM)
    player.play()
    player.auto_play_tick()
    assert any(e.event_type == ReplayEventType.REPLAY_FINISHED for e in player.events)
