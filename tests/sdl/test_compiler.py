"""Tests for StrategyCompiler."""

import pytest

from app.sdl.compiler import CompiledStrategy, StrategyCompiler
from app.sdl.exceptions import SDLValidationError
from app.sdl.models import StrategyDefinition


def test_compile_valid_strategy_returns_compiled_strategy(minimal_strategy_dict) -> None:
    compiled = StrategyCompiler().compile(minimal_strategy_dict)
    assert isinstance(compiled, CompiledStrategy)
    assert compiled.sdl_version == "1.0.0"
    assert len(compiled.checksum) == 64  # sha256 hex digest


def test_compile_invalid_strategy_raises(minimal_strategy_dict) -> None:
    del minimal_strategy_dict["metadata"]
    with pytest.raises(SDLValidationError):
        StrategyCompiler().compile(minimal_strategy_dict)


def test_compile_accepts_strategy_definition_instance(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    compiled = StrategyCompiler().compile(definition)
    assert compiled.definition == definition


def test_execution_order_respects_dependencies(minimal_strategy_dict) -> None:
    minimal_strategy_dict["indicators"] = [
        {"name": "fast_ma", "type": "SMA"},
        {"name": "slow_ma", "type": "SMA"},
    ]
    minimal_strategy_dict["entry_rules"] = [
        {"name": "cross_up", "condition": "x", "depends_on": ["fast_ma", "slow_ma"]}
    ]
    compiled = StrategyCompiler().compile(minimal_strategy_dict)
    order = compiled.execution_order
    assert order.index("fast_ma") < order.index("cross_up")
    assert order.index("slow_ma") < order.index("cross_up")


def test_compile_run_alias_matches_compile(minimal_strategy_dict) -> None:
    compiler = StrategyCompiler()
    via_compile = compiler.compile(minimal_strategy_dict)
    via_run = compiler.run(minimal_strategy_dict)
    assert via_compile.checksum == via_run.checksum


def test_checksum_is_stable_across_recompiles(minimal_strategy_dict) -> None:
    compiler = StrategyCompiler()
    first = compiler.compile(minimal_strategy_dict)
    second = compiler.compile(minimal_strategy_dict)
    assert first.checksum == second.checksum


def test_checksum_differs_for_different_strategies(minimal_strategy_dict, full_strategy_dict) -> None:
    compiler = StrategyCompiler()
    a = compiler.compile(minimal_strategy_dict)
    b = compiler.compile(full_strategy_dict)
    assert a.checksum != b.checksum


def test_compile_all_bundled_examples(example_path) -> None:
    from app.sdl.parser import StrategyParser

    data = StrategyParser().parse_file(example_path)
    compiled = StrategyCompiler().compile(data)
    assert compiled.checksum
