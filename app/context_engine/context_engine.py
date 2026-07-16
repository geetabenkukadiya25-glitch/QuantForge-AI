"""Top-level facade for the Market Context Engine.

`MarketContextEngine` composes `ContextBuilder`, `ContextValidator`, and
`ContextRegistry` into the single entrypoint most callers need. It never
generates buy/sell signals -- it only describes the current market
state, per `PROJECT_VISION.md`'s "Context Before Decision" principle.
Implements `BaseEngine` (`run` aliases `build_context`), consistent with
the constitution's engine-based architecture rule.
"""

from pathlib import Path
from typing import Any

from app.context_engine.builder import ContextBuilder
from app.context_engine.exceptions import ContextValidationError
from app.context_engine.models import ContextSnapshot
from app.context_engine.registry import ContextRegistry, ContextSummary
from app.context_engine.serializer import ContextSerializer
from app.context_engine.validator import ContextValidator, ValidationResult
from app.core.base_engine import BaseEngine
from app.core.feature_flags import FeatureFlagManager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketContextEngine(BaseEngine):
    """Builds, validates, serializes, and stores standardized market context."""

    name = "MarketContextEngine"

    def __init__(
        self,
        builder: ContextBuilder | None = None,
        validator: ContextValidator | None = None,
        registry: ContextRegistry | None = None,
        serializer: ContextSerializer | None = None,
        feature_flags: FeatureFlagManager | None = None,
    ) -> None:
        self._feature_flags = feature_flags or FeatureFlagManager()
        self._builder = builder or ContextBuilder(feature_flags=self._feature_flags)
        self._validator = validator or ContextValidator()
        self._registry = registry or ContextRegistry()
        self._serializer = serializer or ContextSerializer()

    def run(self, *args: Any, **kwargs: Any) -> ContextSnapshot:
        """`BaseEngine` entrypoint; delegates to `build_context`."""
        return self.build_context(*args, **kwargs)

    def build_context(self, **kwargs: Any) -> ContextSnapshot:
        """Build and validate a `ContextSnapshot`.

        Accepts the same keyword arguments as `ContextBuilder.build`.

        Raises:
            ContextBuildError: if the inputs are structurally invalid.
            ContextValidationError: if the built snapshot fails semantic validation.
        """
        snapshot = self._builder.build(**kwargs)
        result = self.validate(snapshot)
        if not result.is_valid:
            raise ContextValidationError(result.errors)
        return snapshot

    def validate(self, snapshot: ContextSnapshot) -> ValidationResult:
        """Validate an already-built snapshot without raising."""
        return self._validator.validate(snapshot)

    def save(self, snapshot: ContextSnapshot, overwrite: bool = False) -> Path:
        """Persist `snapshot` to the context registry."""
        return self._registry.save(snapshot, overwrite=overwrite)

    def load(self, snapshot_id: str) -> ContextSnapshot:
        """Load a previously saved snapshot by id."""
        return self._registry.load(snapshot_id)

    def delete(self, snapshot_id: str) -> None:
        """Delete a previously saved snapshot by id."""
        self._registry.delete(snapshot_id)

    def list_snapshots(self) -> list[ContextSummary]:
        """List every snapshot currently stored in the context registry."""
        return self._registry.list()

    @property
    def feature_flags(self) -> FeatureFlagManager:
        """The `FeatureFlagManager` this engine's builder resolves flags against."""
        return self._feature_flags
