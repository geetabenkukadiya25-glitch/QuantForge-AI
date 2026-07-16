"""Strategy builder (placeholder).

Will translate AI-extracted or user-defined strategy specifications into
concrete `BaseStrategy` implementations, persisted under
`app/strategies/generated/`.
"""

from typing import Any

from app.core.base_strategy import BaseStrategy
from app.core.exceptions import NotImplementedYetError


class StrategyBuilder:
    """Builds executable strategy objects from a strategy specification."""

    def build(self, specification: dict[str, Any]) -> BaseStrategy:
        """Build a `BaseStrategy` from a spec. Not implemented until Phase 2."""
        raise NotImplementedYetError(
            "StrategyBuilder.build", phase="Phase 2 (AI Strategy Builder)"
        )
