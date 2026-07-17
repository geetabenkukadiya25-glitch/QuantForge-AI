"""The full outcome report of a `StrategyBuilder` build attempt.

Distinct from `StrategyModel` (the pure output artifact): `StrategyResult`
additionally carries the validation report, so callers that want full
build introspection (without exception handling) can inspect exactly
what passed/failed.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.strategy_builder.models import StrategyModel
from app.strategy_builder.validator import ValidationResult


@dataclass(frozen=True)
class StrategyResult:
    """The outcome of one `StrategyBuilder.try_build()` call."""

    model: StrategyModel | None
    validation: ValidationResult
    built_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        """True only if validation passed *and* a model was produced."""
        return self.validation.is_valid and self.model is not None
