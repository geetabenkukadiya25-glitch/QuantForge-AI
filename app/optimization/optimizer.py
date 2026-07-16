"""Optimization engine (placeholder).

Will search a strategy's parameter space (grid/random/Bayesian) to
maximize a chosen performance metric across historical data.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.exceptions import NotImplementedYetError


class OptimizationEngine(BaseEngine):
    """Optimizes strategy parameters against historical backtests."""

    name = "OptimizationEngine"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 5 (Optimization)."""
        raise NotImplementedYetError("OptimizationEngine.run", phase="Phase 5 (Optimization)")
