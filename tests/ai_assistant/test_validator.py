"""Tests for `AssistantValidator`."""

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import AssistantConfiguration
from app.ai_assistant.validator import AssistantValidator
from tests.ai_assistant.conftest import make_context


def test_valid_query_passes(full_context):
    context = make_context(full_context, "Explain optimization")
    result = AssistantValidator().validate(context)
    assert result.is_valid


def test_empty_query_fails(full_context):
    context = make_context(full_context, "")
    result = AssistantValidator().validate(context)
    assert not result.is_valid
    assert any("empty" in issue.message.lower() for issue in result.errors)


def test_whitespace_only_query_fails(full_context):
    context = make_context(full_context, "   ")
    result = AssistantValidator().validate(context)
    assert not result.is_valid


def test_too_short_query_fails(full_context):
    from dataclasses import replace

    context = replace(full_context, query="a", configuration=AssistantConfiguration(min_keyword_length=3))
    result = AssistantValidator().validate(context)
    assert not result.is_valid
    assert any("at least 3" in issue.message.lower() for issue in result.errors)


def test_no_registries_attached_warns():
    context = AssistantContext(query="hello world", configuration=AssistantConfiguration())
    result = AssistantValidator().validate(context)
    assert result.is_valid
    assert any("no registry" in issue.message.lower() for issue in result.warnings)


def test_some_registries_attached_no_warning(full_context):
    context = make_context(full_context, "hello world")
    result = AssistantValidator().validate(context)
    assert not any("no registry" in issue.message.lower() for issue in result.warnings)


def test_report_formats_pass_and_fail(full_context):
    passing = AssistantValidator().validate(make_context(full_context, "Explain optimization"))
    assert "PASSED" in passing.report()

    failing = AssistantValidator().validate(make_context(full_context, ""))
    assert "FAILED" in failing.report()


def test_issue_str_includes_severity_and_path(full_context):
    context = make_context(full_context, "")
    result = AssistantValidator().validate(context)
    text = str(result.errors[0])
    assert "[error]" in text
    assert "query" in text
