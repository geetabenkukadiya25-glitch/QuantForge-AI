"""MT5 Expert Advisor generator (placeholder).

Will translate a validated `BaseStrategy` into deployable MQL5 source
code for MetaTrader 5.
"""

from typing import Any

from app.core.base_strategy import BaseStrategy
from app.core.exceptions import NotImplementedYetError


class EAGenerator:
    """Generates MQL5 Expert Advisor source code from a strategy."""

    def generate(self, strategy: BaseStrategy, **kwargs: Any) -> str:
        """Not implemented until Phase 9 (MT5 EA Generator)."""
        raise NotImplementedYetError(
            "EAGenerator.generate", phase="Phase 9 (MT5 EA Generator)"
        )
