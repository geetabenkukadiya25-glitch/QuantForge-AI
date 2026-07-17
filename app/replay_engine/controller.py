"""`ReplayController`: the main object driving interactive replay.

Combines a `ReplayCursor`, a `ReplayPlayer`, and the precomputed
`ReplayFrameSource` into synchronized, cursor-scoped views over the Chart
Engine's candles, the Indicator Engine's series, the Smart Money Engine's
detections, and a supplied Backtesting Engine result. Every accessor here
exposes data ONLY up to the cursor's current index -- never beyond it --
so every downstream view (chart, indicator panel, trade markers) stays in
lockstep with the cursor, per the Phase 12 SYNC requirement. This is the
object a Streamlit dashboard drives directly; it never places a trade,
never optimizes, and never modifies the strategy it visualizes.
"""

from dataclasses import dataclass, field

import pandas as pd

from app.replay_engine.context import ReplayContext
from app.replay_engine.cursor import ReplayCursor
from app.replay_engine.frame import ReplayFrameSource, build_frame, build_frame_source
from app.replay_engine.models import ReplayEvent, ReplayEventType, ReplayFrame, ReplaySpeed, ReplayTimeline, TradeLifecycleMarker
from app.replay_engine.player import ReplayPlayer


@dataclass
class ReplayController:
    """Drives one interactive replay session over a `ReplayContext`/`ReplayTimeline`."""

    context: ReplayContext
    timeline: ReplayTimeline
    frame_source: ReplayFrameSource = field(init=False)
    cursor: ReplayCursor = field(init=False)
    player: ReplayPlayer = field(init=False)

    def __post_init__(self) -> None:
        self.frame_source = build_frame_source(self.context)
        self.cursor = ReplayCursor(timeline=self.timeline)
        self.player = ReplayPlayer(cursor=self.cursor, speed=self.context.configuration.default_speed)

    @property
    def current_frame(self) -> ReplayFrame:
        """The `ReplayFrame` snapshot at the cursor's current position."""
        return build_frame(self.context, self.frame_source, self.timeline.start_index + self.cursor.index)

    @property
    def events(self) -> tuple[ReplayEvent, ...]:
        return tuple(self.player.events)

    def synced_candles(self) -> pd.DataFrame:
        """The Chart Engine slice up to (and including) the cursor -- never beyond it."""
        start = self.timeline.start_index
        end = start + self.cursor.index
        return self.context.data.iloc[start : end + 1]

    def synced_trade_markers(self) -> tuple[TradeLifecycleMarker, ...]:
        """Every trade-lifecycle marker at or before the cursor -- never beyond it."""
        markers: list[TradeLifecycleMarker] = []
        for offset in range(self.cursor.index + 1):
            markers.extend(self.frame_source.markers_by_index.get(self.timeline.start_index + offset, []))
        return tuple(markers)

    def record_signal(self, message: str = "Signal created.") -> None:
        """Manually record a `SIGNAL_CREATED` event at the current frame.

        Replay never re-runs strategy rules itself, so signal detection is
        the caller's responsibility (e.g. a dashboard overlaying its own
        entry/exit markers) -- this only appends the event to the log.
        """
        self.player.events.append(
            ReplayEvent(event_type=ReplayEventType.SIGNAL_CREATED, frame_index=self.cursor.index, datetime=self.cursor.datetime, message=message)
        )

    def play(self) -> None:
        self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def resume(self) -> None:
        self.player.resume()

    def stop(self) -> None:
        self.player.stop()

    def restart(self) -> None:
        self.player.restart()

    def step_forward(self, steps: int = 1) -> int:
        index = self.player.step_forward(steps)
        self._emit_marker_events(index)
        return index

    def step_backward(self, steps: int = 1) -> int:
        return self.player.step_backward(steps)

    def jump_to_candle(self, index: int) -> int:
        result = self.cursor.jump_to_candle(index)
        self._emit_marker_events(result)
        return result

    def jump_to_time(self, datetime_str: str) -> int:
        result = self.cursor.jump_to_time(datetime_str)
        self._emit_marker_events(result)
        return result

    def go_to_beginning(self) -> int:
        return self.cursor.go_to_beginning()

    def go_to_end(self) -> int:
        result = self.cursor.go_to_end()
        self._emit_marker_events(result)
        return result

    def set_speed(self, speed: ReplaySpeed) -> None:
        self.player.set_speed(speed)

    def tick(self) -> int:
        """Advance one auto-play tick and emit any trade-marker events crossed."""
        index = self.player.auto_play_tick()
        self._emit_marker_events(index)
        return index

    def _emit_marker_events(self, index: int) -> None:
        global_index = self.timeline.start_index + index
        for marker in self.frame_source.markers_by_index.get(global_index, []):
            event_type = ReplayEventType.TRADE_OPENED if marker.marker_type == "OPEN" else ReplayEventType.TRADE_CLOSED
            self.player.events.append(
                ReplayEvent(event_type=event_type, frame_index=index, datetime=self.timeline.frame_datetimes[index], message=f"{marker.marker_type} trade {marker.trade_id}")
            )
