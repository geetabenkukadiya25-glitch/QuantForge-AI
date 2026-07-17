"""`ReplayCursor`: a mutable position tracker within a `ReplayTimeline`.

Pure navigation -- forward, backward, jump-to-candle, jump-to-time,
go-to-beginning, go-to-end. It never triggers computation itself and
never carries execution logic; `ReplayController` reads the cursor's
current index to build the corresponding `ReplayFrame` on demand.
"""

from dataclasses import dataclass, field

from app.replay_engine.exceptions import ReplayNavigationError
from app.replay_engine.models import ReplayTimeline


@dataclass
class ReplayCursor:
    """Tracks the current frame index within one `ReplayTimeline`."""

    timeline: ReplayTimeline
    _index: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.timeline.total_frames == 0:
            raise ReplayNavigationError("Cannot create a cursor over an empty timeline.")
        self._index = 0

    @property
    def index(self) -> int:
        """The current frame index, local to the timeline (0-based)."""
        return self._index

    @property
    def datetime(self) -> str:
        return self.timeline.frame_datetimes[self._index]

    @property
    def at_beginning(self) -> bool:
        return self._index == 0

    @property
    def at_end(self) -> bool:
        return self._index == self.timeline.total_frames - 1

    def forward(self, steps: int = 1) -> int:
        """Advance `steps` frames (clamped to the timeline's last frame)."""
        target = min(self._index + steps, self.timeline.total_frames - 1)
        self._set_index(target)
        return self._index

    def backward(self, steps: int = 1) -> int:
        """Rewind `steps` frames (clamped to the timeline's first frame)."""
        target = max(self._index - steps, 0)
        self._set_index(target)
        return self._index

    def jump_to_candle(self, index: int) -> int:
        """Jump directly to timeline-local frame `index`.

        Raises:
            ReplayNavigationError: if `index` is out of range.
        """
        self._set_index(index)
        return self._index

    def jump_to_time(self, datetime_str: str) -> int:
        """Jump to the frame whose datetime exactly matches `datetime_str`.

        Raises:
            ReplayNavigationError: if no frame has that datetime.
        """
        try:
            target = self.timeline.frame_datetimes.index(datetime_str)
        except ValueError as exc:
            raise ReplayNavigationError(f"No frame at datetime {datetime_str!r}.") from exc
        self._index = target
        return self._index

    def go_to_beginning(self) -> int:
        self._index = 0
        return self._index

    def go_to_end(self) -> int:
        self._index = self.timeline.total_frames - 1
        return self._index

    def _set_index(self, index: int) -> None:
        if not (0 <= index < self.timeline.total_frames):
            raise ReplayNavigationError(f"Index {index} is out of range [0, {self.timeline.total_frames - 1}].")
        self._index = index
