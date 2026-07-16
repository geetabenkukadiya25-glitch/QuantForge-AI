"""Abstract base class for trading strategies.

Both AI-generated and manually authored strategies will implement this
interface, keeping the backtesting/optimization engines decoupled from how
a strategy's signals are produced.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Common contract every trading strategy must satisfy."""

    name: str = "BaseStrategy"

    @abstractmethod
    def generate_signals(self, data: Any) -> Any:
        """Compute entry/exit signals from historical market data."""
        raise NotImplementedError

    @abstractmethod
    def get_parameters(self) -> dict[str, Any]:
        """Return the strategy's tunable parameters (for optimization)."""
        raise NotImplementedError
