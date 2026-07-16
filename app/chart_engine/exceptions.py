"""Exception hierarchy for the chart engine.

All exceptions derive from `app.core.exceptions.EngineError` so callers
can catch broadly (`except EngineError`) or narrowly
(`except ChartDataError`).
"""

from app.core.exceptions import EngineError


class ChartEngineError(EngineError):
    """Base class for all chart_engine errors."""


class ChartDataError(ChartEngineError):
    """Raised when input data is missing the columns required to chart it."""


class DrawingError(ChartEngineError):
    """Raised when a drawing object cannot be built or rendered."""


class ExportError(ChartEngineError):
    """Raised when a chart cannot be exported to the requested format."""
