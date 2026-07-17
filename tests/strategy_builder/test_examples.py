"""Integration tests against the real bundled SDL examples (Phase 4)."""

from pathlib import Path

import pytest

from app.sdl import StrategyParser
from app.sdl import StrategyValidator as SDLValidator
from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.context import StrategyContext

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "app" / "sdl" / "examples"


def _load_sdl(name: str):
    data = StrategyParser().parse_file(EXAMPLES_DIR / f"{name}.yaml")
    result = SDLValidator().validate(data)
    assert result.is_valid, result.report()
    return result.definition


def test_moving_average_cross_builds_successfully(indicator_registry, smc_registry) -> None:
    sdl = _load_sdl("moving_average_cross")
    context = StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry)
    model = StrategyBuilder().build(context)
    assert model.metadata.id == "moving-average-cross"
    assert len(model.indicators) == 2
    assert len(model.execution_pipeline.steps) > 0


def test_rsi_reversal_builds_successfully(indicator_registry, smc_registry) -> None:
    sdl = _load_sdl("rsi_reversal")
    context = StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry)
    model = StrategyBuilder().build(context)
    assert model.metadata.id == "rsi-reversal"
    assert any(ref.type == "RSI" for ref in model.indicators)


@pytest.mark.parametrize("name", ["london_breakout", "smc_template"])
def test_placeholder_examples_fail_strategy_builder_validation(name, indicator_registry, smc_registry) -> None:
    """These Phase 4 examples use descriptive placeholder indicator types
    (e.g. "SESSION_RANGE_HIGH", "ORDER_BLOCK") that intentionally don't match
    any real registered indicator/detector name -- the Strategy Builder
    should reject them with clear validation errors, not crash.
    """
    from app.strategy_builder.exceptions import StrategyValidationError

    sdl = _load_sdl(name)
    context = StrategyContext(sdl_definition=sdl, indicator_registry=indicator_registry, smc_registry=smc_registry)
    with pytest.raises(StrategyValidationError):
        StrategyBuilder().build(context)
