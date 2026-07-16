"""AI strategy extractor (placeholder).

Will parse a transcript's natural-language description of a trading
strategy into a structured specification consumable by `StrategyBuilder`.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class AIStrategyExtractor:
    """Extracts a structured strategy specification from transcript text."""

    def extract(self, transcript_text: str) -> dict[str, Any]:
        """Not implemented until Phase 2 (YouTube Strategy Import)."""
        raise NotImplementedYetError(
            "AIStrategyExtractor.extract", phase="Phase 2 (YouTube Strategy Import)"
        )
