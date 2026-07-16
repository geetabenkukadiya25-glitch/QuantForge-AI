"""Walk-forward validation engine (placeholder).

Will repeatedly re-optimize and out-of-sample test a strategy across
rolling time windows to assess robustness against overfitting.
"""

from typing import Any

from app.core.base_engine import BaseEngine
from app.core.exceptions import NotImplementedYetError


class WalkForwardEngine(BaseEngine):
    """Runs walk-forward optimization/validation windows."""

    name = "WalkForwardEngine"

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 6 (Walk Forward)."""
        raise NotImplementedYetError("WalkForwardEngine.run", phase="Phase 6 (Walk Forward)")
