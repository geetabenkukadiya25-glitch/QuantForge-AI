"""Exception hierarchy for the historical data engine.

All exceptions derive from `app.core.exceptions.DataError` so callers can
catch broadly (`except DataError`) or narrowly (`except CSVFormatError`).
"""

from app.core.exceptions import DataError


class DataEngineError(DataError):
    """Base class for all data_engine errors."""


class CSVFormatError(DataEngineError):
    """Raised when a CSV file cannot be parsed into standard OHLCV columns."""


class DataValidationError(DataEngineError):
    """Raised when data fails validation and cannot be safely used as-is."""
