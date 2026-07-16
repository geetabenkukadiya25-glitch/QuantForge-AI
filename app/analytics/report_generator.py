"""Report generator (placeholder).

Will render analytics results into shareable reports (HTML/PDF) under
`app/analytics/reports/`.
"""

from typing import Any

from app.core.exceptions import NotImplementedYetError


class ReportGenerator:
    """Generates strategy performance reports."""

    def generate(self, analytics_result: Any, **kwargs: Any) -> Any:
        """Not implemented until Phase 8 (Risk Analysis)."""
        raise NotImplementedYetError(
            "ReportGenerator.generate", phase="Phase 8 (Risk Analysis)"
        )
