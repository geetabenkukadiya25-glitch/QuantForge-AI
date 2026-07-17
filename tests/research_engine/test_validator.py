"""Pre-execution validation for a `ResearchContext`."""

import dataclasses

from app.research_engine.context import ResearchContext, StrategyRecord
from app.research_engine.validator import ResearchValidator


def test_valid_context_passes(research_context) -> None:
    result = ResearchValidator().validate(research_context)
    assert result.is_valid


def test_empty_records_is_rejected(research_configuration) -> None:
    context = ResearchContext(records=(), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid
    assert any("records" in issue.path for issue in result.errors)


def test_single_record_is_valid_but_warns(single_record_context) -> None:
    result = ResearchValidator().validate(single_record_context)
    assert result.is_valid
    assert any("2+" in w.message for w in result.warnings)


def test_duplicate_strategy_ids_are_rejected(record_a_full, research_configuration) -> None:
    context = ResearchContext(records=(record_a_full, record_a_full), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid
    assert any("Duplicate" in e.message for e in result.errors)


def test_identity_mismatch_between_strategy_and_backtest_is_rejected(record_a_full, record_b_bare, research_configuration) -> None:
    mismatched = StrategyRecord(strategy_model=record_a_full.strategy_model, backtest_result=record_b_bare.backtest_result)
    context = ResearchContext(records=(mismatched,), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid
    assert any("does not match" in e.message for e in result.errors)


def test_unsupported_strategy_model_version_is_rejected(record_b_bare, research_configuration) -> None:
    bad_metadata = record_b_bare.strategy_model.metadata.model_copy(update={"model_version": "0.0.1"})
    bad_model = record_b_bare.strategy_model.model_copy(update={"metadata": bad_metadata})
    record = StrategyRecord(strategy_model=bad_model, backtest_result=record_b_bare.backtest_result)
    context = ResearchContext(records=(record,), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid


def test_unsupported_backtest_result_version_is_rejected(record_b_bare, research_configuration) -> None:
    bad_metadata = record_b_bare.backtest_result.metadata.model_copy(update={"result_version": "0.0.1"})
    bad_result = record_b_bare.backtest_result.model_copy(update={"metadata": bad_metadata})
    record = StrategyRecord(strategy_model=record_b_bare.strategy_model, backtest_result=bad_result)
    context = ResearchContext(records=(record,), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid


def test_unsupported_optimization_result_version_is_rejected(record_a_full, research_configuration) -> None:
    bad_metadata = record_a_full.optimization_result.metadata.model_copy(update={"result_version": "0.0.1"})
    bad_opt = record_a_full.optimization_result.model_copy(update={"metadata": bad_metadata})
    record = dataclasses.replace(record_a_full, optimization_result=bad_opt)
    context = ResearchContext(records=(record,), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid


def test_unsupported_validation_result_version_is_rejected(record_a_full, research_configuration) -> None:
    bad_metadata = record_a_full.validation_result.metadata.model_copy(update={"result_version": "0.0.1"})
    bad_val = record_a_full.validation_result.model_copy(update={"metadata": bad_metadata})
    record = dataclasses.replace(record_a_full, validation_result=bad_val)
    context = ResearchContext(records=(record,), configuration=research_configuration)
    result = ResearchValidator().validate(context)
    assert not result.is_valid


def test_report_lists_every_error() -> None:
    from app.research_engine.validator import ResearchCheckResult, ResearchIssue

    result = ResearchCheckResult(errors=[ResearchIssue(path="a", message="bad")])
    assert "FAILED" in result.report()
    assert "a: bad" in result.report()
