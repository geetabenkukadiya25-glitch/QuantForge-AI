"""Analytics engine (placeholder).

Will compute performance/risk metrics (Sharpe, Sortino, max drawdown,
CAGR, win rate, ...) and produce Plotly charts under
`app/analytics/charts/`.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.exceptions import NotImplementedYetError


class AnalyticsEngine(BaseEngine):
    """Computes performance and risk analytics from backtest results."""

    name = "AnalyticsEngine"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 8 (Risk Analysis)."""
        raise NotImplementedYetError("AnalyticsEngine.run", phase="Phase 8 (Risk Analysis)")
