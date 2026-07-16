"""Top-level facade for the Indicator Engine.

`IndicatorEngine` composes `IndicatorRegistry`, `IndicatorFactory`, and
`IndicatorValidator` into the single entrypoint most callers need. It is
responsible ONLY for calculating indicators -- it never generates
buy/sell signals, never contains strategy logic, and never executes
trades. Implements `BaseEngine` (`run` aliases `compute`), consistent
with the constitution's engine-based architecture rule.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.feature_flags import FeatureFlagManager
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.exceptions import IndicatorValidationError
from app.indicator_engine.factory import IndicatorFactory
from app.indicator_engine.metadata import IndicatorMetadata
from app.indicator_engine.registry import IndicatorRegistry
from app.indicator_engine.result import IndicatorResult
from app.indicator_engine.validator import IndicatorValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class IndicatorEngine(BaseEngine):
    """Computes registered indicators over standardized OHLCV context."""

    name = "IndicatorEngine"

    def __init__(
        self,
        registry: IndicatorRegistry | None = None,
        factory: IndicatorFactory | None = None,
        validator: IndicatorValidator | None = None,
        feature_flags: FeatureFlagManager | None = None,
    ) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._registry = registry or IndicatorRegistry(feature_flags=self._feature_flags)
        if not self._registry.list():
            self._registry.register_builtins()
        self._factory = factory or IndicatorFactory(self._registry)
        self._validator = validator or IndicatorValidator()

    def run(self, *args: Any, **kwargs: Any) -> IndicatorResult:
        """`BaseEngine` entrypoint; delegates to `compute`."""
        return self.compute(*args, **kwargs)

    def compute(self, name: str, context: IndicatorContext, **params: Any) -> IndicatorResult:
        """Compute indicator `name` over `context` with `params`.

        Raises:
            IndicatorNotFoundError: if `name` isn't registered.
            IndicatorDisabledError: if `name` is registered but disabled.
            IndicatorValidationError: if parameters, input, or output fail validation.
        """
        metadata = self._registry.get_metadata(name)

        param_result = self._validator.validate_parameters(metadata, params)
        if not param_result.is_valid:
            raise IndicatorValidationError(param_result.errors)

        input_result = self._validator.validate_input(metadata, context)
        if not input_result.is_valid:
            raise IndicatorValidationError(input_result.errors)

        indicator = self._factory.create(name, **params)
        result = indicator.compute(context)

        output_result = self._validator.validate_output(metadata, result)
        if not output_result.is_valid:
            raise IndicatorValidationError(output_result.errors)

        logger.info("Computed indicator %r for %s %s", name, context.symbol, context.timeframe)
        return result

    def list_indicators(self, include_disabled: bool = True) -> list[IndicatorMetadata]:
        """List every registered indicator's metadata."""
        return self._registry.list(include_disabled=include_disabled)

    def search(self, query: str | None = None, category: str | None = None) -> list[IndicatorMetadata]:
        """Search registered indicators by name substring and/or category."""
        return self._registry.search(query=query, category=category)

    def enable(self, name: str) -> None:
        self._registry.enable(name)

    def disable(self, name: str) -> None:
        self._registry.disable(name)

    @property
    def registry(self) -> IndicatorRegistry:
        return self._registry

    @property
    def feature_flags(self) -> FeatureFlagManager:
        return self._feature_flags
