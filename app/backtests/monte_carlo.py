"""Monte Carlo simulation engine (placeholder).

Will resample/perturb historical trade sequences to estimate the
distribution of possible equity-curve outcomes and drawdown risk.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.exceptions import NotImplementedYetError


class MonteCarloEngine(BaseEngine):
    """Runs Monte Carlo simulations over backtest results."""

    name = "MonteCarloEngine"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 7 (Monte Carlo)."""
        raise NotImplementedYetError("MonteCarloEngine.run", phase="Phase 7 (Monte Carlo)")
