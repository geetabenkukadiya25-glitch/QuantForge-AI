"""Tests for the SDL Pydantic schema (StrategyDefinition and sections)."""

import pytest
from pydantic import ValidationError

from app.sdl.models import StrategyDefinition


def test_minimal_document_is_valid(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    assert definition.metadata.id == "minimal-strategy"
    assert definition.entry_rules == []


def test_full_document_round_trips_through_model(full_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(full_strategy_dict)
    assert definition.trade_management.partial_close[0].close_pct == 50
    assert definition.scoring_rules[0].weight == 1.0


def test_missing_required_field_raises(minimal_strategy_dict) -> None:
    del minimal_strategy_dict["symbols"]
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_empty_symbols_list_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["symbols"] = []
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_unknown_top_level_field_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["not_a_real_section"] = {}
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_unknown_nested_field_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["metadata"]["unexpected"] = "value"
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_wrong_type_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["symbols"] = "EURUSD"  # should be a list
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_invalid_bias_direction_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["bias"] = {"direction": "sideways"}
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_partial_close_pct_out_of_range_raises(minimal_strategy_dict) -> None:
    minimal_strategy_dict["trade_management"] = {"partial_close": [{"trigger": 1.0, "close_pct": 150}]}
    with pytest.raises(ValidationError):
        StrategyDefinition.model_validate(minimal_strategy_dict)


def test_defaults_applied(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    assert definition.metadata.strategy_version == "1.0.0"
    assert definition.tags == []
    assert definition.sessions == []
