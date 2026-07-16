"""Project-wide exception hierarchy.

Every custom exception in QuantForge AI derives from `QuantForgeError`,
letting callers catch broadly (`except QuantForgeError`) or narrowly
(`except DataError`) as needed.
"""


class QuantForgeError(Exception):
    """Base class for all QuantForge AI errors."""


class ConfigurationError(QuantForgeError):
    """Raised when configuration is missing, invalid, or inconsistent."""


class DataError(QuantForgeError):
    """Raised for historical/market data loading or validation failures."""


class EngineError(QuantForgeError):
    """Raised when a research engine (backtest, optimization, ...) fails."""


class NotImplementedYetError(QuantForgeError):
    """Raised by placeholder modules reserved for a future development phase."""

    def __init__(self, feature: str, phase: str = "a future phase") -> None:
        super().__init__(f"'{feature}' is not implemented yet; scheduled for {phase}.")
