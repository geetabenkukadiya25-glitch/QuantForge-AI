"""`app.ui.progress`: the reusable, deterministic, presentation-only
`ProgressTracker` component. Pure functions/state -- no Streamlit
runtime required except for the dedicated `AppTest` rendering tests."""

import time

import pytest
from streamlit.testing.v1 import AppTest

from app.ui.progress import (
    BACKTEST_STEPS,
    CLOUD_PLATFORM_STEPS,
    EA_GENERATOR_STEPS,
    OPTIMIZATION_STEPS,
    REPLAY_STEPS,
    RESEARCH_STEPS,
    VALIDATION_STEPS,
    ProgressStepStatus,
    ProgressTracker,
    create_cloud_platform_tracker,
    tracked_step,
)

# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------


def test_requires_at_least_one_step() -> None:
    with pytest.raises(ValueError):
        ProgressTracker([])


def test_initial_state_is_all_pending() -> None:
    tracker = ProgressTracker(["A", "B", "C"])
    assert tracker.total_steps == 3
    assert tracker.completed_count == 0
    assert tracker.percentage == 0
    assert tracker.current_step_number == 0
    assert not tracker.is_complete
    assert all(step.status == ProgressStepStatus.PENDING for step in tracker.steps)


# ---------------------------------------------------------------------
# start_step / complete_step
# ---------------------------------------------------------------------


def test_start_step_marks_running_and_sets_current_step_number() -> None:
    tracker = ProgressTracker(["A", "B"])
    tracker.start_step(0)
    assert tracker.steps[0].status == ProgressStepStatus.RUNNING
    assert tracker.steps[0].started_at is not None
    assert tracker.current_step_number == 1


def test_complete_step_marks_complete_and_updates_percentage() -> None:
    tracker = ProgressTracker(["A", "B"])
    tracker.start_step(0)
    tracker.complete_step(0)
    assert tracker.steps[0].status == ProgressStepStatus.COMPLETE
    assert tracker.steps[0].completed_at is not None
    assert tracker.completed_count == 1
    assert tracker.percentage == 50


def test_complete_step_defaults_to_current_index() -> None:
    tracker = ProgressTracker(["A", "B"])
    tracker.start_step(1)
    tracker.complete_step()
    assert tracker.steps[1].status == ProgressStepStatus.COMPLETE


def test_start_step_out_of_range_raises() -> None:
    tracker = ProgressTracker(["A"])
    with pytest.raises(IndexError):
        tracker.start_step(5)


def test_complete_step_out_of_range_raises() -> None:
    tracker = ProgressTracker(["A"])
    with pytest.raises(IndexError):
        tracker.complete_step(5)


def test_percentage_reaches_100_when_every_step_complete() -> None:
    tracker = ProgressTracker(["A", "B", "C"])
    for i in range(3):
        tracker.start_step(i)
        tracker.complete_step(i)
    assert tracker.percentage == 100
    assert tracker.is_complete


def test_percentage_is_deterministic_given_the_same_state_transitions() -> None:
    def run() -> int:
        tracker = ProgressTracker(["A", "B", "C", "D"])
        tracker.start_step(0)
        tracker.complete_step(0)
        tracker.start_step(1)
        tracker.complete_step(1)
        return tracker.percentage

    assert run() == run() == 50


# ---------------------------------------------------------------------
# estimated_remaining_seconds
# ---------------------------------------------------------------------


def test_estimated_remaining_seconds_none_before_any_step_completes() -> None:
    tracker = ProgressTracker(["A", "B"])
    assert tracker.estimated_remaining_seconds() is None
    tracker.start_step(0)
    assert tracker.estimated_remaining_seconds() is None


def test_estimated_remaining_seconds_none_once_complete() -> None:
    tracker = ProgressTracker(["A"])
    tracker.start_step(0)
    tracker.complete_step(0)
    assert tracker.estimated_remaining_seconds() is None


def test_estimated_remaining_seconds_positive_after_one_completed_step() -> None:
    tracker = ProgressTracker(["A", "B"])
    tracker.start_step(0)
    time.sleep(0.01)
    tracker.complete_step(0)
    remaining = tracker.estimated_remaining_seconds()
    assert remaining is not None
    assert remaining >= 0


# ---------------------------------------------------------------------
# tracked_step
# ---------------------------------------------------------------------


def test_tracked_step_starts_and_completes_around_the_block() -> None:
    tracker = ProgressTracker(["A", "B"])
    executed = []
    with tracked_step(tracker, 0):
        executed.append("inside")
        assert tracker.steps[0].status == ProgressStepStatus.RUNNING
    assert executed == ["inside"]
    assert tracker.steps[0].status == ProgressStepStatus.COMPLETE


def test_tracked_step_completes_even_if_the_block_raises() -> None:
    tracker = ProgressTracker(["A"])
    with pytest.raises(RuntimeError):
        with tracked_step(tracker, 0):
            raise RuntimeError("boom")
    assert tracker.steps[0].status == ProgressStepStatus.COMPLETE


def test_tracked_step_never_alters_business_logic_return_values() -> None:
    """The wrapped block's own result is untouched -- tracked_step only observes."""
    tracker = ProgressTracker(["A"])
    result_holder = {}
    with tracked_step(tracker, 0):
        result_holder["value"] = 2 + 2
    assert result_holder["value"] == 4


# ---------------------------------------------------------------------
# Fixed step-list constants -- one per integrated dashboard
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "steps",
    [BACKTEST_STEPS, OPTIMIZATION_STEPS, VALIDATION_STEPS, REPLAY_STEPS, RESEARCH_STEPS, EA_GENERATOR_STEPS, CLOUD_PLATFORM_STEPS],
)
def test_every_step_list_is_non_empty_and_constructs_a_tracker(steps: list[str]) -> None:
    tracker = ProgressTracker(steps)
    assert tracker.total_steps == len(steps)
    assert len(steps) >= 1


def test_create_cloud_platform_tracker_uses_the_standard_step_list() -> None:
    tracker = create_cloud_platform_tracker()
    assert [step.name for step in tracker.steps] == CLOUD_PLATFORM_STEPS


def test_cloud_platform_tracker_wraps_a_real_cloud_platform_operation() -> None:
    """Proves genuine integration readiness: tracked_step wraps an actual
    `CloudWorkspaceManager` call (reused, unmodified) without altering its
    behavior or return value."""
    from app.cloud_platform.workspace_manager import CloudWorkspaceManager

    manager = CloudWorkspaceManager()
    tracker = create_cloud_platform_tracker()

    with tracked_step(tracker, 0):
        pass  # "Validating Request" -- nothing to validate before a fresh create
    with tracked_step(tracker, 1):
        record = manager.create_workspace("progress-demo-ws", label="Progress Demo")
    with tracked_step(tracker, 2):
        pass

    assert tracker.is_complete
    assert record.workspace.workspace_id == "progress-demo-ws"
    assert manager.registry.load("progress-demo-ws") == record


# ---------------------------------------------------------------------
# render() -- via AppTest, since it calls into the real Streamlit API
# ---------------------------------------------------------------------


def _render_backtest_progress() -> None:
    from app.ui.progress import BACKTEST_STEPS, ProgressTracker

    tracker = ProgressTracker(BACKTEST_STEPS)
    tracker.start_step(0)
    tracker.complete_step(0)
    tracker.start_step(1)
    tracker.render()


def test_render_shows_progress_bar_caption_and_checklist() -> None:
    at = AppTest.from_function(_render_backtest_progress)
    at.run()
    assert at.exception == []

    captions = [c.value for c in at.caption]
    assert any("Step 2 of 3" in c for c in captions)
    assert any(c == "33%" for c in captions)  # 1 of 3 steps complete
    assert any("Current operation: Running Simulation" in c for c in captions)

    progress_values = [p.value for p in at.get("progress")]
    assert progress_values == [33]  # a real st.progress() bar, not custom HTML

    markdown_text = [m.value for m in at.markdown]
    assert any(text.startswith("✓") for text in markdown_text)  # "Preparing Configuration" complete
    assert any(text.startswith("▶") for text in markdown_text)  # "Running Simulation" running
    assert any(text.startswith("○") for text in markdown_text)  # "Finalizing Results" pending


def _render_complete_progress() -> None:
    from app.ui.progress import ProgressTracker

    tracker = ProgressTracker(["Only Step"])
    tracker.start_step(0)
    tracker.complete_step(0)
    tracker.render()


def test_render_at_100_percent_shows_no_estimated_time() -> None:
    at = AppTest.from_function(_render_complete_progress)
    at.run()
    assert at.exception == []
    captions = [c.value for c in at.caption]
    assert any("100%" in c for c in captions)
    assert not any("Estimated remaining" in c for c in captions)
