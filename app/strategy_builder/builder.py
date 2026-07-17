"""Builds executable `StrategyModel`s from SDL documents.

`StrategyBuilder` resolves indicator/detector/rule references, validates
dependencies, and compiles the result into an immutable `StrategyModel`.
It does not execute trades, place orders, backtest, optimize parameters,
or generate AI decisions -- it only builds and validates executable
strategy definitions.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.base_engine import BaseEngine
from app.strategy_builder.compiler import StrategyCompiler
from app.strategy_builder.context import StrategyContext
from app.strategy_builder.exceptions import StrategyValidationError
from app.strategy_builder.models import StrategyModel
from app.strategy_builder.resolution import resolve_components
from app.strategy_builder.result import StrategyResult
from app.strategy_builder.validator import StrategyValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseStrategyBuilder(BaseEngine, ABC):
    """Common contract every strategy-building strategy (pun intended) implements.

    An extensibility point: future builder variants (e.g. one optimized
    for a different SDL revision) can implement this without changing
    callers that only depend on the interface.
    """

    name = "BaseStrategyBuilder"

    @abstractmethod
    def build(self, context: StrategyContext) -> StrategyModel:
        """Build and return a `StrategyModel`.

        Raises:
            StrategyValidationError: if the strategy fails validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> StrategyModel:
        """`BaseEngine` entrypoint; delegates to `build`."""
        return self.build(*args, **kwargs)


class StrategyBuilder(BaseStrategyBuilder):
    """The default `BaseStrategyBuilder` implementation."""

    name = "StrategyBuilder"

    def __init__(
        self,
        validator: StrategyValidator | None = None,
        compiler: StrategyCompiler | None = None,
    ) -> None:
        self._validator = validator or StrategyValidator()
        self._compiler = compiler or StrategyCompiler()

    def build(self, context: StrategyContext) -> StrategyModel:
        """Resolve, validate, and compile `context` into a `StrategyModel`.

        Raises:
            StrategyValidationError: if resolution/validation fails.
        """
        result = self.try_build(context)
        if not result.is_valid:
            raise StrategyValidationError(result.validation.errors)
        assert result.model is not None  # guaranteed by is_valid
        return result.model

    def try_build(self, context: StrategyContext) -> StrategyResult:
        """Resolve, validate, and (if valid) compile `context`. Never raises."""
        resolved = resolve_components(context)
        validation = self._validator.validate(context.sdl_definition, resolved)

        if not validation.is_valid:
            return StrategyResult(model=None, validation=validation)

        model = self._compiler.compile(context.sdl_definition, resolved)
        return StrategyResult(model=model, validation=validation)
