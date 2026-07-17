"""`ResearchEngine`: the top-level facade -- execute/try_execute."""

import pytest

from app.research_engine.engine import ResearchEngine
from app.research_engine.exceptions import ResearchValidationError
from app.research_engine.runner import ResearchSession


def test_execute_returns_a_research_result(record_a_full, record_b_bare, research_configuration) -> None:
    engine = ResearchEngine()
    result = engine.execute((record_a_full, record_b_bare), research_configuration)
    assert result.result_id
    assert len(result.rankings) == 2


def test_try_execute_returns_a_session(record_a_full, record_b_bare, research_configuration) -> None:
    engine = ResearchEngine()
    session = engine.try_execute((record_a_full, record_b_bare), research_configuration)
    assert isinstance(session, ResearchSession)
    assert session.is_successful


def test_execute_raises_on_invalid_context(research_configuration) -> None:
    engine = ResearchEngine()
    with pytest.raises(ResearchValidationError):
        engine.execute((), research_configuration)


def test_run_aliases_execute(record_a_full, record_b_bare, research_configuration) -> None:
    engine = ResearchEngine()
    result = engine.run((record_a_full, record_b_bare), research_configuration)
    assert result.result_id


def test_execute_never_optimizes_never_backtests(record_b_bare, research_configuration) -> None:
    """A record with only Strategy Builder + Backtesting Engine outputs still
    produces a complete result -- proving Research Engine never re-invokes
    Optimization/Validation logic of its own."""
    engine = ResearchEngine()
    result = engine.execute((record_b_bare,), research_configuration)
    assert result.rankings[0].confidence_score.has_validation is False
