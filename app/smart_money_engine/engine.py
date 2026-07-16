"""Top-level facade for the Smart Money Engine.

`SmartMoneyEngine` composes `SMCRegistry`, `SMCFactory`, and
`SMCValidator` into the single entrypoint most callers need. It is
responsible ONLY for detecting and describing Smart Money structures --
it never generates buy/sell signals, never contains strategy logic, and
never executes trades. Implements `BaseEngine` (`run` aliases `detect`),
consistent with the constitution's engine-based architecture rule.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.feature_flags import FeatureFlagManager
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.exceptions import SMCValidationError
from app.smart_money_engine.factory import SMCFactory
from app.smart_money_engine.metadata import SMCMetadata
from app.smart_money_engine.registry import SMCRegistry
from app.smart_money_engine.result import SMCResult
from app.smart_money_engine.validator import SMCValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SmartMoneyEngine(BaseEngine):
    """Runs registered Smart Money detectors over standardized OHLCV context."""

    name = "SmartMoneyEngine"

    def __init__(
        self,
        registry: SMCRegistry | None = None,
        factory: SMCFactory | None = None,
        validator: SMCValidator | None = None,
        feature_flags: FeatureFlagManager | None = None,
    ) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._registry = registry or SMCRegistry(feature_flags=self._feature_flags)
        if not self._registry.list():
            self._registry.register_builtins()
        self._factory = factory or SMCFactory(self._registry)
        self._validator = validator or SMCValidator()

    def run(self, *args: Any, **kwargs: Any) -> SMCResult:
        """`BaseEngine` entrypoint; delegates to `detect`."""
        return self.detect(*args, **kwargs)

    def detect(self, name: str, context: SMCContext, **params: Any) -> SMCResult:
        """Run detector `name` over `context` with `params`.

        Raises:
            SMCDetectorNotFoundError: if `name` isn't registered.
            SMCDetectorDisabledError: if `name` is registered but disabled.
            SMCValidationError: if parameters, input, or output fail validation.
        """
        metadata = self._registry.get_metadata(name)

        param_result = self._validator.validate_parameters(metadata, params)
        if not param_result.is_valid:
            raise SMCValidationError(param_result.errors)

        input_result = self._validator.validate_input(metadata, context)
        if not input_result.is_valid:
            raise SMCValidationError(input_result.errors)

        detector = self._factory.create(name, **params)
        result = detector.detect(context)

        output_result = self._validator.validate_output(metadata, result, len(context.data))
        if not output_result.is_valid:
            raise SMCValidationError(output_result.errors)

        logger.info(
            "Ran detector %r for %s %s: %d detection(s)",
            name,
            context.symbol,
            context.timeframe,
            len(result.detections),
        )
        return result

    def list_detectors(self, include_disabled: bool = True) -> list[SMCMetadata]:
        """List every registered detector's metadata."""
        return self._registry.list(include_disabled=include_disabled)

    def search(self, query: str | None = None, category: str | None = None) -> list[SMCMetadata]:
        """Search registered detectors by name substring and/or category."""
        return self._registry.search(query=query, category=category)

    def enable(self, name: str) -> None:
        self._registry.enable(name)

    def disable(self, name: str) -> None:
        self._registry.disable(name)

    @property
    def registry(self) -> SMCRegistry:
        return self._registry

    @property
    def feature_flags(self) -> FeatureFlagManager:
        return self._feature_flags
