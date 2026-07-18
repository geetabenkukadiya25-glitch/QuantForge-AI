"""`AIStrategyExtractionEngine`: the top-level facade -- execute/try_execute."""

import pytest

from app.ai_extraction.engine import AIStrategyExtractionEngine
from app.ai_extraction.exceptions import ExtractionValidationError
from app.ai_extraction.models import SourceType
from app.ai_extraction.runner import ExtractionSession
from tests.ai_extraction.conftest import SAMPLE_MARKDOWN


def test_execute_returns_an_extraction_result(indicator_registry, smc_registry) -> None:
    engine = AIStrategyExtractionEngine()
    result = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert result.result_id
    assert result.strategy_name == "Golden Cross Trend Strategy"


def test_try_execute_returns_a_session() -> None:
    engine = AIStrategyExtractionEngine()
    session = engine.try_execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN)
    assert isinstance(session, ExtractionSession)
    assert session.is_successful


def test_execute_raises_on_invalid_context() -> None:
    engine = AIStrategyExtractionEngine()
    with pytest.raises(ExtractionValidationError):
        engine.execute("", SourceType.PLAIN_TEXT)


def test_run_aliases_execute() -> None:
    engine = AIStrategyExtractionEngine()
    result = engine.run(SAMPLE_MARKDOWN, SourceType.MARKDOWN)
    assert result.result_id


def test_execute_without_registries_falls_back_to_defaults() -> None:
    """No caller-supplied registries -- confirms the engine can run
    fully standalone without any other engine's state."""
    engine = AIStrategyExtractionEngine()
    result = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN)
    assert any(m.matched_type == "SMA" for m in result.indicators)
