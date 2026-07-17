"""`ReplayRunner`: validate, build timeline, precompute, compile -- and build interactive controllers."""

import pandas as pd
import pytest

from app.replay_engine.context import ReplayContext
from app.replay_engine.controller import ReplayController
from app.replay_engine.exceptions import ReplayValidationError
from app.replay_engine.models import ReplayConfiguration
from app.replay_engine.runner import ReplayRunner, SessionStatus


def test_try_execute_succeeds_for_a_valid_context(replay_context) -> None:
    session = ReplayRunner().try_execute(replay_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_raises_on_invalid_context(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1] * 5})
    context = ReplayContext(data=data, configuration=replay_configuration)
    with pytest.raises(ReplayValidationError):
        ReplayRunner().execute(context)


def test_try_execute_never_raises_on_invalid_context(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1] * 5})
    context = ReplayContext(data=data, configuration=replay_configuration)
    session = ReplayRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED
    assert not session.validation.is_valid


def test_execute_populates_statistics(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    assert result.statistics.total_frames == len(replay_context.data)
    assert result.statistics.indicators_included == ("fast_sma", "slow_sma")
    assert result.statistics.total_trade_markers > 0


def test_build_controller_returns_an_interactive_controller(replay_context) -> None:
    controller = ReplayRunner().build_controller(replay_context)
    assert isinstance(controller, ReplayController)
    assert controller.cursor.index == 0


def test_build_controller_raises_on_invalid_context(replay_configuration: ReplayConfiguration) -> None:
    data = pd.DataFrame({"Datetime": pd.date_range("2024-01-01", periods=5, freq="h"), "Open": [1] * 5})
    context = ReplayContext(data=data, configuration=replay_configuration)
    with pytest.raises(ReplayValidationError):
        ReplayRunner().build_controller(context)


def test_run_aliases_execute(replay_context) -> None:
    result_via_run = ReplayRunner().run(replay_context)
    assert result_via_run.result_id
