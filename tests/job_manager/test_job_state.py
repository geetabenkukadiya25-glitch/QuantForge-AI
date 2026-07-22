from app.job_manager.job_state import JobState, is_terminal


def test_terminal_states():
    assert is_terminal(JobState.COMPLETED)
    assert is_terminal(JobState.CANCELLED)
    assert is_terminal(JobState.FAILED)


def test_non_terminal_states():
    assert not is_terminal(JobState.QUEUED)
    assert not is_terminal(JobState.RUNNING)


def test_state_values_are_strings():
    assert JobState.QUEUED.value == "QUEUED"
    assert JobState.RUNNING.value == "RUNNING"
