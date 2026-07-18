"""Tests for app.ea_generator.validator."""

from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.models import EAGeneratorConfiguration
from app.ea_generator.validator import EAGeneratorValidator


def test_valid_context_passes(ea_context) -> None:
    result = EAGeneratorValidator().validate(ea_context)
    assert result.is_valid


def test_full_context_passes(full_ea_context) -> None:
    result = EAGeneratorValidator().validate(full_ea_context)
    assert result.is_valid


def test_rejects_filename_without_mq5_extension(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="EA.txt"))
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid


def test_rejects_filename_with_path_separator(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="dir/EA.mq5"))
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid


def test_rejects_filename_with_backslash(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="dir\\EA.mq5"))
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid


def test_rejects_filename_with_dotdot(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="..EA.mq5"))
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid


def test_rejects_filename_with_reserved_character(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="EA?.mq5"))
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid


def test_accepts_filename_case_insensitively(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="EA.MQ5"))
    result = EAGeneratorValidator().validate(context)
    assert result.is_valid


def test_warns_when_no_risk_exit_configured(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(stop_loss_points=0, take_profit_points=0))
    result = EAGeneratorValidator().validate(context)
    assert result.is_valid
    assert any("risk exit" in str(w) for w in result.warnings)


def test_no_warning_when_stop_loss_configured(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(stop_loss_points=10, take_profit_points=0))
    result = EAGeneratorValidator().validate(context)
    assert not any("risk exit" in str(w) for w in result.warnings)


def test_rejects_mismatched_validation_result_strategy_id(strategy_model_b, ea_configuration, validation_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_b, configuration=ea_configuration, validation_result=validation_result_a)
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid
    assert any("validation_result" in issue.path for issue in result.errors)


def test_rejects_mismatched_optimization_result_strategy_id(strategy_model_b, ea_configuration, optimization_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_b, configuration=ea_configuration, optimization_result=optimization_result_a)
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid
    assert any("optimization_result" in issue.path for issue in result.errors)


def test_rejects_mismatched_research_result_strategy_id(strategy_model_b, ea_configuration, research_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_b, configuration=ea_configuration, research_result=research_result_a)
    result = EAGeneratorValidator().validate(context)
    assert not result.is_valid
    assert any("research_result" in issue.path for issue in result.errors)


def test_accepts_matching_portfolio_result(strategy_model_a, ea_configuration, portfolio_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, portfolio_result=portfolio_result_a)
    result = EAGeneratorValidator().validate(context)
    assert result.is_valid


def test_accepts_matching_research_result(strategy_model_a, ea_configuration, research_result_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=ea_configuration, research_result=research_result_a)
    result = EAGeneratorValidator().validate(context)
    assert result.is_valid


def test_check_result_report_mentions_pass_or_fail(ea_context) -> None:
    result = EAGeneratorValidator().validate(ea_context)
    assert "PASSED" in result.report()


def test_failed_check_result_report_mentions_failed(strategy_model_a) -> None:
    context = EAGeneratorContext(strategy_model=strategy_model_a, configuration=EAGeneratorConfiguration(output_filename="bad.txt"))
    result = EAGeneratorValidator().validate(context)
    assert "FAILED" in result.report()


def test_issue_str_includes_severity_and_path() -> None:
    from app.ea_generator.validator import EAGeneratorIssue

    issue = EAGeneratorIssue(path="configuration.x", message="bad value", severity="error")
    assert str(issue) == "[error] configuration.x: bad value"
