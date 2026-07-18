"""Tests for `PortfolioValidator`."""

from dataclasses import replace

from app.portfolio_engine.context import PortfolioContext
from app.portfolio_engine.models import AllocationMethod, ManualWeight, PortfolioConfiguration
from app.portfolio_engine.validator import PortfolioValidator


def test_valid_context_passes(portfolio_context):
    result = PortfolioValidator().validate(portfolio_context)
    assert result.is_valid


def test_too_few_strategies_fails(entry_a_full):
    context = PortfolioContext(entries=(entry_a_full,), configuration=PortfolioConfiguration(min_strategies_required=2))
    result = PortfolioValidator().validate(context)
    assert not result.is_valid
    assert any("at least 2" in issue.message.lower() for issue in result.errors)


def test_duplicate_strategy_ids_fail(entry_a_full):
    config = PortfolioConfiguration(min_strategies_required=1)
    context = PortfolioContext(entries=(entry_a_full, entry_a_full), configuration=config)
    result = PortfolioValidator().validate(context)
    assert not result.is_valid
    assert any("duplicate" in issue.message.lower() for issue in result.errors)


def test_report_formats_pass_and_fail(portfolio_context, entry_a_full):
    passing = PortfolioValidator().validate(portfolio_context)
    assert "PASSED" in passing.report()

    failing_context = PortfolioContext(entries=(entry_a_full,), configuration=PortfolioConfiguration(min_strategies_required=5))
    failing = PortfolioValidator().validate(failing_context)
    assert "FAILED" in failing.report()


def test_single_strategy_warns_about_diversification(entry_a_full):
    context = PortfolioContext(entries=(entry_a_full,), configuration=PortfolioConfiguration(min_strategies_required=1))
    result = PortfolioValidator().validate(context)
    assert result.is_valid
    assert any("2+" in issue.message for issue in result.warnings)


def test_manual_weight_missing_supplied_weight_warns(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    config = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT, manual_weights=(ManualWeight(strategy_id=id_a, weight=1.0),))
    context = PortfolioContext(entries=(entry_a_full, entry_b_bare), configuration=config)
    result = PortfolioValidator().validate(context)
    assert result.is_valid
    assert any("manual weight" in issue.message.lower() for issue in result.warnings)


def test_manual_weight_fully_supplied_no_warning(entry_a_full, entry_b_bare):
    id_a = entry_a_full.strategy_model.metadata.id
    id_b = entry_b_bare.strategy_model.metadata.id
    config = PortfolioConfiguration(allocation_method=AllocationMethod.MANUAL_WEIGHT, manual_weights=(ManualWeight(strategy_id=id_a, weight=1.0), ManualWeight(strategy_id=id_b, weight=1.0)))
    context = PortfolioContext(entries=(entry_a_full, entry_b_bare), configuration=config)
    result = PortfolioValidator().validate(context)
    assert not any("manual weight" in issue.message.lower() for issue in result.warnings)


def test_bad_strategy_model_version_fails(entry_a_full, entry_b_bare):
    # StrategyModel/BacktestResult are frozen PYDANTIC models -- use `model_copy(update=...)`,
    # not `dataclasses.replace` (that only works on the dataclass-based PortfolioStrategyEntry).
    bad_metadata = entry_a_full.strategy_model.metadata.model_copy(update={"model_version": "0.0.1"})
    bad_model = entry_a_full.strategy_model.model_copy(update={"metadata": bad_metadata})
    bad_entry = replace(entry_a_full, strategy_model=bad_model)
    context = PortfolioContext(entries=(bad_entry, entry_b_bare), configuration=PortfolioConfiguration())
    result = PortfolioValidator().validate(context)
    assert not result.is_valid
    assert any("strategymodel version" in issue.message.lower() for issue in result.errors)


def test_bad_backtest_result_version_fails(entry_a_full, entry_b_bare):
    bad_metadata = entry_a_full.backtest_result.metadata.model_copy(update={"result_version": "0.0.1"})
    bad_backtest = entry_a_full.backtest_result.model_copy(update={"metadata": bad_metadata})
    bad_entry = replace(entry_a_full, backtest_result=bad_backtest)
    context = PortfolioContext(entries=(bad_entry, entry_b_bare), configuration=PortfolioConfiguration())
    result = PortfolioValidator().validate(context)
    assert not result.is_valid
    assert any("backtestresult version" in issue.message.lower() for issue in result.errors)


def test_identity_mismatch_fails(entry_a_full, entry_b_bare):
    mismatched_metadata = entry_a_full.backtest_result.metadata.model_copy(update={"strategy_id": "not-the-real-id"})
    mismatched_backtest = entry_a_full.backtest_result.model_copy(update={"metadata": mismatched_metadata})
    bad_entry = replace(entry_a_full, backtest_result=mismatched_backtest)
    context = PortfolioContext(entries=(bad_entry, entry_b_bare), configuration=PortfolioConfiguration())
    result = PortfolioValidator().validate(context)
    assert not result.is_valid
    assert any("does not match" in issue.message.lower() for issue in result.errors)


def test_issue_str_includes_severity_and_path(entry_a_full):
    context = PortfolioContext(entries=(entry_a_full,), configuration=PortfolioConfiguration(min_strategies_required=3))
    result = PortfolioValidator().validate(context)
    text = str(result.errors[0])
    assert "[error]" in text
    assert "entries" in text
