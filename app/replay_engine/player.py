"""`ReplayPlayer`: the playback state machine (play/pause/resume/stop/restart/step/speed).

Headless and deterministic: this engine has no real-time timer or thread
of its own (a framework placeholder, like Phase 9's `latency_bars`) --
`speed` only governs how many frames `auto_play_tick()` advances per call,
and `ReplaySpeed.MAXIMUM` advances straight to the end in one call.
Wall-clock pacing, if ever added, belongs to the UI layer driving this
player, not this engine (see PROJECT_IDEAS.md). `ReplayPlayer` never
places a trade and never modifies strategy logic -- it only moves a
`ReplayCursor` and records what happened as `ReplayEvent`s.
"""

from dataclasses import dataclass, field

from app.replay_engine.cursor import ReplayCursor
from app.replay_engine.exceptions import ReplayNavigationError
from app.replay_engine.models import PlaybackState, ReplayEvent, ReplayEventType, ReplaySpeed


@dataclass
class ReplayPlayer:
    """Drives one `ReplayCursor` through play/pause/resume/stop/step/speed transitions."""

    cursor: ReplayCursor
    speed: ReplaySpeed = ReplaySpeed.X1
    state: PlaybackState = PlaybackState.STOPPED
    events: list[ReplayEvent] = field(default_factory=list)

    def play(self) -> None:
        """Start playback from the cursor's current position."""
        self.state = PlaybackState.PLAYING
        self._emit(ReplayEventType.REPLAY_STARTED, "Replay started.")

    def pause(self) -> None:
        """Raises: ReplayNavigationError: if not currently playing."""
        if self.state != PlaybackState.PLAYING:
            raise ReplayNavigationError("Cannot pause: replay is not currently playing.")
        self.state = PlaybackState.PAUSED
        self._emit(ReplayEventType.REPLAY_PAUSED, "Replay paused.")

    def resume(self) -> None:
        """Raises: ReplayNavigationError: if not currently paused."""
        if self.state != PlaybackState.PAUSED:
            raise ReplayNavigationError("Cannot resume: replay is not currently paused.")
        self.state = PlaybackState.PLAYING
        self._emit(ReplayEventType.REPLAY_RESUMED, "Replay resumed.")

    def stop(self) -> None:
        """Stop playback and reset the cursor to the beginning."""
        self.state = PlaybackState.STOPPED
        self.cursor.go_to_beginning()

    def restart(self) -> None:
        """Reset the cursor and clear the event log, as if playback never began."""
        self.cursor.go_to_beginning()
        self.state = PlaybackState.STOPPED
        self.events.clear()

    def step_forward(self, steps: int = 1) -> int:
        index = self.cursor.forward(steps)
        self._emit(ReplayEventType.FRAME_CHANGED, f"Advanced to frame {index}.")
        self._check_finished()
        return index

    def step_backward(self, steps: int = 1) -> int:
        index = self.cursor.backward(steps)
        self._emit(ReplayEventType.FRAME_CHANGED, f"Rewound to frame {index}.")
        return index

    def set_speed(self, speed: ReplaySpeed) -> None:
        self.speed = speed

    def auto_play_tick(self) -> int:
        """Advance one auto-play "tick": `speed` frames (or straight to the
        end for `ReplaySpeed.MAXIMUM`). No-op if not currently playing.
        """
        if self.state != PlaybackState.PLAYING:
            return self.cursor.index
        if self.cursor.at_end:
            self._check_finished()
            return self.cursor.index

        if self.speed == ReplaySpeed.MAXIMUM:
            self.cursor.go_to_end()
        else:
            self.cursor.forward(max(1, int(self.speed.value)))

        self._emit(ReplayEventType.FRAME_CHANGED, f"Advanced to frame {self.cursor.index}.")
        self._check_finished()
        return self.cursor.index

    def _check_finished(self) -> None:
        if self.cursor.at_end and self.state == PlaybackState.PLAYING:
            self.state = PlaybackState.FINISHED
            self._emit(ReplayEventType.REPLAY_FINISHED, "Replay finished.")

    def _emit(self, event_type: ReplayEventType, message: str) -> None:
        self.events.append(ReplayEvent(event_type=event_type, frame_index=self.cursor.index, datetime=self.cursor.datetime, message=message))
