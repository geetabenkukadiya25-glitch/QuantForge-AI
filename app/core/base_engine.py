"""Abstract base class for all research-pipeline engines.

Backtesting, optimization, walk-forward, and Monte Carlo engines all
implement this interface so the pipeline can orchestrate them
interchangeably (dependency inversion / Liskov substitution).
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseEngine(ABC):
    """Common contract for every engine in the research pipeline."""

    name: str = "BaseEngine"

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the engine's core computation and return its result."""
        raise NotImplementedError

    def validate_inputs(self, *args: Any, **kwargs: Any) -> None:
        """Validate inputs before `run`. Subclasses override as needed."""
        return None
