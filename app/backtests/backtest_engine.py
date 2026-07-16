"""Backtesting engine (placeholder).

Will run a `BaseStrategy` against historical data using VectorBT and/or
Backtesting.py, producing trade logs and performance summaries for the
analytics module.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.exceptions import NotImplementedYetError


class BacktestEngine(BaseEngine):
    """Executes a strategy backtest over historical data."""

    name = "BacktestEngine"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 4 (Auto Backtest)."""
        raise NotImplementedYetError("BacktestEngine.run", phase="Phase 4 (Auto Backtest)")
