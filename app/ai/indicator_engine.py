"""Technical indicator engine (placeholder).

Will compute technical indicators (via `ta`) on demand for strategies and
expose an indicator catalog the AI strategy builder can reference.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class IndicatorEngine:
    """Computes technical indicators over OHLCV data."""

    def compute(self, data: Any, indicator: str, **params: Any) -> Any:
        """Not implemented until Phase 2 (AI Strategy Builder)."""
        raise NotImplementedYetError(
            "IndicatorEngine.compute", phase="Phase 2 (AI Strategy Builder)"
        )
