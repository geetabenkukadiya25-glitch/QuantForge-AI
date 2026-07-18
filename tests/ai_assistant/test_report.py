"""Tests for `AssistantReport`."""

import pandas as pd

from app.ai_assistant.report import AssistantReport
from app.ai_assistant.runner import AssistantRunner
from tests.ai_assistant.conftest import make_context


def _report(full_context, query="Explain the strategy-alpha strategy"):
    context = make_context(full_context, query)
    result = AssistantRunner().execute(context)
    return AssistantReport(result)


def test_summary_is_dict(full_context):
    report = _report(full_context)
    summary = report.summary()
    assert isinstance(summary, dict)
    assert summary["query"] == "Explain the strategy-alpha strategy"


def test_summary_includes_disclaimer(full_context):
    summary = _report(full_context).summary()
    assert "deterministic" in summary["disclaimer"].lower()


def test_sections_table_has_one_row_per_section(full_context):
    report = _report(full_context)
    table = report.sections_table()
    assert isinstance(table, pd.DataFrame)
    assert len(table) == len(report.result.answer.sections)


def test_items_table_has_source_type_and_item_id_columns(full_context):
    report = _report(full_context)
    table = report.items_table()
    if not table.empty:
        assert "source_type" in table.columns
        assert "item_id" in table.columns


def test_recommendations_table_is_dataframe(full_context):
    report = _report(full_context)
    table = report.recommendations_table()
    assert isinstance(table, pd.DataFrame)


def test_result_property_returns_underlying_result(full_context):
    context = make_context(full_context, "Explain replay")
    result = AssistantRunner().execute(context)
    report = AssistantReport(result)
    assert report.result is result


def test_items_table_empty_for_no_match(full_context):
    report = _report(full_context, "zzznonexistentzzz")
    table = report.items_table()
    assert table.empty
