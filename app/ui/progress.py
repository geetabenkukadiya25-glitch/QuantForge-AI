"""A reusable, deterministic, presentation-only progress tracker for
long-running dashboard operations.

Pure UI-layer component -- no engine, validator, or business logic is
touched or modified. `ProgressTracker` holds a fixed, caller-supplied
sequence of step names (deterministic: the step list never changes at
runtime) and renders a progress bar, the current step, total steps, a
completed-steps checklist (✓), and an estimated remaining time derived
from the average duration of already-completed steps. Callers bracket
their own already-existing sequential calls with `start_step`/
`complete_step` -- this module never calls into any engine itself.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterator

import streamlit as st


class ProgressStepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"


@dataclass
class ProgressStep:
    """One step in a `ProgressTracker`'s fixed sequence."""

    name: str
    status: ProgressStepStatus = ProgressStepStatus.PENDING
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()


@dataclass
class CandleProgress:
    """Fine-grained, within-step progress reported by an engine's optional
    `progress_callback` (e.g. `TradeSimulator`'s candle loop). Purely
    observational -- populated from callback arguments only, never drives
    any calculation."""

    current: int
    total: int
    operation: str
    started_at: datetime

    @property
    def fraction(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(1.0, self.current / self.total)

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.started_at).total_seconds()

    @property
    def items_per_second(self) -> float | None:
        elapsed = self.elapsed_seconds
        if elapsed <= 0 or self.current <= 0:
            return None
        return self.current / elapsed

    @property
    def remaining_seconds(self) -> float | None:
        rate = self.items_per_second
        if rate is None or rate <= 0:
            return None
        return (self.total - self.current) / rate


class ProgressTracker:
    """Tracks and renders progress through a fixed, predefined sequence of steps.

    Deterministic: given the same sequence of `start_step`/`complete_step`
    calls, `percentage`/`completed_count`/`is_complete` are pure functions
    of state. `estimated_remaining_seconds` uses wall-clock step durations
    (inherently variable run to run) purely for display -- it never
    affects control flow, and no business logic depends on it.

    A step may additionally report fine-grained progress within itself
    (e.g. "candle 683,214 of 1,443,451") via `update_item_progress`, fed by
    an engine's optional `progress_callback`. When present, it blends into
    `percentage` so the bar advances continuously through a single long
    step instead of jumping only at step boundaries -- still a pure,
    deterministic function of the reported counts.
    """

    def __init__(self, step_names: list[str]) -> None:
        if not step_names:
            raise ValueError("ProgressTracker requires at least one step.")
        self.steps: list[ProgressStep] = [ProgressStep(name=name) for name in step_names]
        self._current_index: int = -1
        self._item_progress: CandleProgress | None = None

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def current_step_number(self) -> int:
        """1-based number of the current (running or most recently started) step, 0 if not started."""
        return self._current_index + 1

    @property
    def completed_count(self) -> int:
        return sum(1 for step in self.steps if step.status == ProgressStepStatus.COMPLETE)

    @property
    def percentage(self) -> int:
        if self.total_steps == 0:
            return 0
        base = self.completed_count / self.total_steps
        if self._item_progress is not None and 0 <= self._current_index < self.total_steps:
            if self.steps[self._current_index].status == ProgressStepStatus.RUNNING:
                base += self._item_progress.fraction / self.total_steps
        return round(base * 100)

    @property
    def is_complete(self) -> bool:
        return self.completed_count == self.total_steps

    def start_step(self, index: int) -> None:
        """Mark step `index` (0-based) as RUNNING."""
        if not (0 <= index < self.total_steps):
            raise IndexError(f"Step index {index} out of range (0-{self.total_steps - 1}).")
        self._current_index = index
        step = self.steps[index]
        step.status = ProgressStepStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)
        self._item_progress = None

    def complete_step(self, index: int | None = None) -> None:
        """Mark step `index` (or the current step if omitted) as COMPLETE."""
        target = index if index is not None else self._current_index
        if not (0 <= target < self.total_steps):
            raise IndexError(f"Step index {target} out of range (0-{self.total_steps - 1}).")
        step = self.steps[target]
        step.status = ProgressStepStatus.COMPLETE
        step.completed_at = datetime.now(timezone.utc)
        if target == self._current_index:
            self._item_progress = None

    def update_item_progress(self, current: int, total: int, operation: str = "Processing") -> None:
        """Record fine-grained within-step progress -- the shape an
        engine's optional `progress_callback(current, total, operation)`
        reports. Call only while the owning step is RUNNING; presentation-
        only, never mutates step status itself."""
        if self._item_progress is None or self._item_progress.total != total:
            started_at = datetime.now(timezone.utc)
        else:
            started_at = self._item_progress.started_at
        self._item_progress = CandleProgress(current=current, total=total, operation=operation, started_at=started_at)

    @property
    def item_progress(self) -> CandleProgress | None:
        return self._item_progress

    def estimated_remaining_seconds(self) -> float | None:
        """Estimate remaining time. Prefers the observed processing rate
        from active within-step item progress (e.g. candles/sec) when
        available -- far more accurate for one long-running step than the
        step-average fallback, which is used otherwise. Returns `None`
        once complete or with nothing to estimate from yet."""
        if self.is_complete:
            return None
        if self._item_progress is not None:
            item_remaining = self._item_progress.remaining_seconds
            if item_remaining is not None:
                return item_remaining
        durations = [step.duration_seconds for step in self.steps if step.duration_seconds is not None]
        if not durations:
            return None
        average = sum(durations) / len(durations)
        remaining_steps = self.total_steps - self.completed_count
        return average * remaining_steps

    def render(self, container=None) -> None:
        """Render the tracker's current state: a real `st.progress()` bar
        (never a custom HTML widget) plus percentage, step counter,
        estimated remaining time, and current operation -- with a
        candle/item-level breakdown (count, elapsed, rate) when the
        running step has reported `update_item_progress` -- followed by
        the completed-steps checklist. Presentation-only -- never mutates
        tracker state."""
        target = container if container is not None else st

        if 0 <= self._current_index < self.total_steps:
            current_label = self.steps[self._current_index].name
            running_item_progress = self._item_progress if self.steps[self._current_index].status == ProgressStepStatus.RUNNING else None
        else:
            current_label = "Not started"
            running_item_progress = None

        target.markdown("**Progress**")
        target.progress(self.percentage / 100)
        target.caption(f"{self.percentage}%")
        target.caption(f"Step {min(self.current_step_number, self.total_steps)} of {self.total_steps}")

        remaining = self.estimated_remaining_seconds()
        if remaining is not None:
            target.caption(f"Estimated remaining time: {self._format_duration(remaining)}")

        if running_item_progress is not None:
            target.caption(running_item_progress.operation)
            target.caption(f"{running_item_progress.current:,} / {running_item_progress.total:,}")
            rate = running_item_progress.items_per_second
            if rate is not None:
                target.caption(f"{rate:,.0f} candles/sec")
            target.caption(f"Elapsed: {self._format_duration(running_item_progress.elapsed_seconds)}")
        else:
            target.caption(f"Current operation: {current_label}")

        for step in self.steps:
            if step.status == ProgressStepStatus.COMPLETE:
                target.markdown(f"✓ {step.name}")
            elif step.status == ProgressStepStatus.RUNNING:
                target.markdown(f"▶ {step.name}")
            else:
                target.markdown(f"○ {step.name}")

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """`HH:MM:SS` for readability at candle-processing timescales."""
        seconds = max(0, round(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, sec = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"


@contextmanager
def tracked_step(tracker: ProgressTracker, index: int, placeholder=None) -> Iterator[ProgressTracker]:
    """Bracket one already-existing call with `start_step`/`complete_step`
    and a re-render, so the caller's own logic never has to repeat that
    boilerplate. Presentation-only: never wraps, retries, or alters
    whatever runs inside the `with` block -- only observes its start/end.
    """
    tracker.start_step(index)
    if placeholder is not None:
        with placeholder.container():
            tracker.render()
    try:
        yield tracker
    finally:
        tracker.complete_step(index)
        if placeholder is not None:
            with placeholder.container():
                tracker.render()


def make_item_progress_callback(tracker: ProgressTracker, placeholder=None):
    """Build a `(current, total, operation) -> None` callback suitable for
    an engine's optional `progress_callback` parameter (e.g.
    `BacktestingEngine.try_execute(..., progress_callback=...)`).

    Each call records the reported counts on `tracker` via
    `update_item_progress` and re-renders into `placeholder` (if given).
    The engine itself throttles how often it calls back, so this stays
    lightweight -- purely presentational, it never touches engine state,
    trading logic, or results.
    """

    def _callback(current: int, total: int, operation: str) -> None:
        tracker.update_item_progress(current, total, operation)
        if placeholder is not None:
            with placeholder.container():
                tracker.render()

    return _callback


# Fixed, deterministic step sequences for each long-running dashboard
# workflow. Each list is presentation-only scaffolding -- it names the
# same phases those pages already execute sequentially; it never adds,
# removes, or reorders an engine call.
BACKTEST_STEPS = ["Preparing Configuration", "Running Simulation", "Finalizing Results"]
OPTIMIZATION_STEPS = ["Building Parameter Space", "Running Optimization", "Finalizing Results"]
VALIDATION_STEPS = ["Building Parameter Space", "Running Optimization", "Running Walk Forward & Monte Carlo Validation", "Finalizing Results"]
REPLAY_STEPS = ["Building Strategy Overlay", "Running Backtest Overlay"]
RESEARCH_STEPS = ["Building & Backtesting Strategies", "Running Research Analysis", "Finalizing Results"]
EA_GENERATOR_STEPS = ["Building Strategy Model", "Generating EA Source Code", "Finalizing Results"]
CLOUD_PLATFORM_STEPS = ["Validating Request", "Executing Cloud Platform Operation", "Finalizing Results"]


def create_cloud_platform_tracker() -> ProgressTracker:
    """Factory for a `ProgressTracker` over the standard Cloud Platform
    operation phases (`CLOUD_PLATFORM_STEPS`).

    The Cloud Platform Foundation/Workspace Management/Artifact Registry/
    Versioning modules (`app.cloud_platform.*`) are deliberately offline,
    in-memory, and have no Streamlit page of their own yet. This tracker
    lets any caller -- a future page, or a script driving
    `CloudWorkspaceManager`/`CloudArtifactManager`/`CloudVersionManager`
    directly -- wrap a Cloud Platform operation with the same
    `tracked_step` pattern every dashboard integration in this module uses.
    """
    return ProgressTracker(CLOUD_PLATFORM_STEPS)
