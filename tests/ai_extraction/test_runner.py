"""`ExtractionRunner`: the full pipeline orchestration."""

import pytest

from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.exceptions import ExtractionValidationError
from app.ai_extraction.models import SourceType
from app.ai_extraction.runner import ExtractionRunner, SessionStatus


def test_try_execute_succeeds_for_a_valid_context(extraction_context) -> None:
    session = ExtractionRunner().try_execute(extraction_context)
    assert session.is_successful
    assert session.status == SessionStatus.COMPLETED
    assert session.result is not None


def test_execute_raises_on_invalid_context(extraction_configuration) -> None:
    context = ExtractionContext(raw_text="", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    with pytest.raises(ExtractionValidationError):
        ExtractionRunner().execute(context)


def test_try_execute_never_raises_on_invalid_context(extraction_configuration) -> None:
    context = ExtractionContext(raw_text="", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    session = ExtractionRunner().try_execute(context)
    assert not session.is_successful
    assert session.status == SessionStatus.FAILED


def test_result_contains_every_pipeline_category(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    assert result.indicators
    assert result.entry_rules
    assert result.exit_rules
    assert result.risk_mentions
    assert result.sessions
    assert result.timeframes
    assert result.confidence.overall_confidence > 0
    assert result.generated_sdl_yaml
    assert result.sdl_validation.is_valid


def test_sparse_document_produces_missing_information(sparse_context) -> None:
    result = ExtractionRunner().execute(sparse_context)
    assert "entry_rules" in result.missing_information.missing_items
    assert "symbol" in result.missing_information.missing_items


def test_strategy_name_hint_overrides_detected_name(extraction_configuration, indicator_registry, smc_registry) -> None:
    from tests.ai_extraction.conftest import SAMPLE_MARKDOWN

    configuration = extraction_configuration.model_copy(update={"strategy_name_hint": "My Custom Name"})
    context = ExtractionContext(raw_text=SAMPLE_MARKDOWN, source_type=SourceType.MARKDOWN, configuration=configuration, indicator_registry=indicator_registry, smc_registry=smc_registry)
    result = ExtractionRunner().execute(context)
    assert result.strategy_name == "My Custom Name"


def test_run_aliases_execute(extraction_context) -> None:
    result = ExtractionRunner().run(extraction_context)
    assert result.result_id
