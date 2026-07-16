"""Tests for StrategyValidator (structural + semantic validation)."""

from app.sdl.models import StrategyDefinition
from app.sdl.validator import StrategyValidator


def test_valid_minimal_document(minimal_strategy_dict) -> None:
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert result.is_valid
    assert result.definition is not None


def test_valid_full_document(full_strategy_dict) -> None:
    result = StrategyValidator().validate(full_strategy_dict)
    assert result.is_valid, result.report()


def test_missing_required_field_reported(minimal_strategy_dict) -> None:
    del minimal_strategy_dict["metadata"]
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("metadata" in issue.path for issue in result.errors)


def test_wrong_type_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["timeframes"] = "H1"
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid


def test_unknown_field_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["bogus_section"] = {}
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("bogus_section" in issue.path for issue in result.errors)


def test_unsupported_sdl_version_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["metadata"]["sdl_version"] = "9.9.9"
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("sdl_version" in issue.path for issue in result.errors)


def test_duplicate_rule_names_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["entry_rules"] = [
        {"name": "same", "condition": "a"},
        {"name": "same", "condition": "b"},
    ]
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("Duplicate name" in issue.message for issue in result.errors)


def test_duplicate_names_across_different_sections_are_allowed(minimal_strategy_dict) -> None:
    minimal_strategy_dict["entry_rules"] = [{"name": "same", "condition": "a"}]
    minimal_strategy_dict["exit_rules"] = [{"name": "same", "condition": "b"}]
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert result.is_valid


def test_circular_dependency_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["indicators"] = [
        {"name": "a", "type": "SMA", "depends_on": ["b"]},
        {"name": "b", "type": "SMA", "depends_on": ["a"]},
    ]
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("Circular dependency" in issue.message for issue in result.errors)


def test_self_referential_dependency_reported(minimal_strategy_dict) -> None:
    minimal_strategy_dict["indicators"] = [{"name": "a", "type": "SMA", "depends_on": ["a"]}]
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert not result.is_valid
    assert any("Circular dependency" in issue.message for issue in result.errors)


def test_no_entry_rules_produces_warning_not_error(minimal_strategy_dict) -> None:
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert result.is_valid
    assert any("entry_rules" in issue.path for issue in result.warnings)


def test_primary_timeframe_not_in_timeframes_warns(minimal_strategy_dict) -> None:
    minimal_strategy_dict["primary_timeframe"] = "H4"
    result = StrategyValidator().validate(minimal_strategy_dict)
    assert result.is_valid
    assert any("primary_timeframe" in issue.path for issue in result.warnings)


def test_validate_accepts_strategy_definition_instance(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    result = StrategyValidator().validate(definition)
    assert result.is_valid


def test_report_is_human_readable(minimal_strategy_dict) -> None:
    del minimal_strategy_dict["market"]
    result = StrategyValidator().validate(minimal_strategy_dict)
    report = result.report()
    assert "FAILED" in report
    assert "market" in report


def test_all_bundled_examples_are_valid(example_path) -> None:
    from app.sdl.parser import StrategyParser

    data = StrategyParser().parse_file(example_path)
    result = StrategyValidator().validate(data)
    assert result.is_valid, result.report()
