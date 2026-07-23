"""Exceptions for Risk Analytics (Phase 17.7)."""


class RiskAnalyticsError(Exception):
    """Base exception for `app.risk_analytics`."""


class RiskReportNotFoundError(RiskAnalyticsError):
    """Raised when a risk report id has no matching record."""


class UnsupportedSourceError(RiskAnalyticsError):
    """Raised when a requested analysis source cannot be resolved into a
    concrete result object (e.g. an unknown job id, or a job whose result
    is no longer resident in Job Manager)."""


class InsufficientDataError(RiskAnalyticsError):
    """Raised when an analytic is requested over data too sparse to
    produce a meaningful result (e.g. VaR over zero trades) -- never
    silently fabricated, always raised explicitly."""
