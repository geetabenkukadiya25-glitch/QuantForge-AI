"""Tests for BaseStrategyBuilder / StrategyBuilder."""

import pytest

from app.strategy_builder.builder import BaseStrategyBuilder, StrategyBuilder
from app.strategy_builder.exceptions import StrategyValidationError
from app.strategy_builder.models import StrategyModel
from app.strategy_builder.result import StrategyResult


def test_builder_is_base_strategy_builder() -> None:
    assert issubclass(StrategyBuilder, BaseStrategyBuilder)


def test_build_returns_strategy_model(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    assert isinstance(model, StrategyModel)


def test_run_aliases_build(valid_context) -> None:
    builder = StrategyBuilder()
    via_run = builder.run(valid_context)
    via_build = builder.build(valid_context)
    assert via_run.checksum == via_build.checksum


def test_build_raises_on_invalid_strategy(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_REAL"}])
    with pytest.raises(StrategyValidationError):
        StrategyBuilder().build(context)


def test_try_build_never_raises_and_reports_failure(context_factory) -> None:
    context = context_factory(indicators=[{"name": "x", "type": "NOT_REAL"}])
    result = StrategyBuilder().try_build(context)
    assert isinstance(result, StrategyResult)
    assert not result.is_valid
    assert result.model is None
    assert result.validation.errors


def test_try_build_success_case(valid_context) -> None:
    result = StrategyBuilder().try_build(valid_context)
    assert result.is_valid
    assert result.model is not None
    assert not result.validation.errors
