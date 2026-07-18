"""Pre-execution validation for an `ExtractionContext`."""

from app.ai_extraction.context import ExtractionContext
from app.ai_extraction.models import SourceType
from app.ai_extraction.validator import ExtractionValidator


def test_valid_context_passes(extraction_context) -> None:
    result = ExtractionValidator().validate(extraction_context)
    assert result.is_valid


def test_empty_text_is_rejected(extraction_configuration) -> None:
    context = ExtractionContext(raw_text="", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    result = ExtractionValidator().validate(context)
    assert not result.is_valid
    assert any("raw_text" in issue.path for issue in result.errors)


def test_whitespace_only_text_is_rejected(extraction_configuration) -> None:
    context = ExtractionContext(raw_text="   \n\n  ", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    result = ExtractionValidator().validate(context)
    assert not result.is_valid


def test_too_short_text_is_rejected(extraction_configuration) -> None:
    context = ExtractionContext(raw_text="short", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    result = ExtractionValidator().validate(context)
    assert not result.is_valid
    assert any("too short" in issue.message for issue in result.errors)


def test_report_lists_every_error() -> None:
    from app.ai_extraction.validator import ExtractionCheckResult, ExtractionIssue

    result = ExtractionCheckResult(errors=[ExtractionIssue(path="a", message="bad")])
    assert "FAILED" in result.report()
    assert "a: bad" in result.report()
