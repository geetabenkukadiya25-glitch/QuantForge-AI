"""Tests for app.ea_generator.report."""

import pandas as pd

from app.ea_generator.engine import EAGeneratorEngine
from app.ea_generator.report import EAGeneratorReport


def _result(strategy_model_a, ea_configuration):
    return EAGeneratorEngine().execute(strategy_model_a, ea_configuration)


def test_summary_contains_strategy_id(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    summary = report.summary()
    assert summary["strategy_id"] == strategy_model_a.metadata.id


def test_summary_contains_checksum(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    report = EAGeneratorReport(result)
    assert report.summary()["checksum"] == result.checksum


def test_inputs_table_is_dataframe(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    table = report.inputs_table()
    assert isinstance(table, pd.DataFrame)
    assert len(table) >= 5


def test_indicators_table_has_rows(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    table = report.indicators_table()
    assert len(table) == 2


def test_risk_report_matches_configuration(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    risk = report.risk_report()
    assert risk["lot_size"] == ea_configuration.lot_size


def test_entry_rules_table_has_rows(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    table = report.entry_rules_table()
    assert len(table) == 2


def test_exit_rules_table_has_rows(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    table = report.exit_rules_table()
    assert len(table) == 1


def test_filters_table_is_empty_when_no_filters(strategy_model_a, ea_configuration) -> None:
    report = EAGeneratorReport(_result(strategy_model_a, ea_configuration))
    table = report.filters_table()
    assert table.empty


def test_source_preview_truncates_long_source(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    report = EAGeneratorReport(result)
    preview = report.source_preview(max_lines=3)
    assert preview.count("\n") <= 3
    assert "more line" in preview


def test_source_preview_full_when_short_enough(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    report = EAGeneratorReport(result)
    preview = report.source_preview(max_lines=10_000)
    assert preview == result.source_code.rstrip("\n") or preview == "\n".join(result.source_code.splitlines())


def test_result_property_returns_same_result(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    report = EAGeneratorReport(result)
    assert report.result is result
