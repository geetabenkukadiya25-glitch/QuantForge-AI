"""Instantiates Smart Money detector objects by name.

Composes `SMCRegistry` (to resolve name -> class) rather than holding
its own class mapping, so there is exactly one place detectors are
registered.
"""

from typing import Any

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.exceptions import SMCDetectorDisabledError
from app.smart_money_engine.registry import SMCRegistry


class SMCFactory:
    """Creates configured `BaseSMCDetector` instances from the registry."""

    def __init__(self, registry: SMCRegistry | None = None) -> None:
        self._registry = registry or SMCRegistry()

    def create(self, name: str, **params: Any) -> BaseSMCDetector:
        """Instantiate the registered detector `name` with `params`.

        Raises:
            SMCDetectorNotFoundError: if `name` isn't registered.
            SMCDetectorDisabledError: if `name` is registered but disabled.
        """
        if not self._registry.is_enabled(name):
            raise SMCDetectorDisabledError(f"Detector {name!r} is disabled.")
        detector_cls = self._registry.load(name)
        return detector_cls(**params)
