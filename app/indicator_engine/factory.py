"""Instantiates indicator objects by name.

Composes `IndicatorRegistry` (to resolve name -> class) rather than
holding its own class mapping, so there is exactly one place indicators
are registered.
"""

from typing import Any

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.exceptions import IndicatorDisabledError
from app.indicator_engine.registry import IndicatorRegistry


class IndicatorFactory:
    """Creates configured `BaseIndicator` instances from the registry."""

    def __init__(self, registry: IndicatorRegistry | None = None) -> None:
        self._registry = registry or IndicatorRegistry()

    def create(self, name: str, **params: Any) -> BaseIndicator:
        """Instantiate the registered indicator `name` with `params`.

        Raises:
            IndicatorNotFoundError: if `name` isn't registered.
            IndicatorDisabledError: if `name` is registered but disabled.
        """
        if not self._registry.is_enabled(name):
            raise IndicatorDisabledError(f"Indicator {name!r} is disabled.")
        indicator_cls = self._registry.load(name)
        return indicator_cls(**params)
