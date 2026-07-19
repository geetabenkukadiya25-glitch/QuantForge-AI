"""Exception hierarchy for the Cloud Platform Foundation.

All exceptions derive from `app.core.exceptions.QuantForgeError` so
callers can catch broadly (`except QuantForgeError`) or narrowly
(`except CloudValidationError`). This phase is offline metadata
management only -- none of these exceptions carry network, auth, or
sync failure semantics; those belong to later phases.
"""

from typing import TYPE_CHECKING

from app.core.exceptions import QuantForgeError

if TYPE_CHECKING:
    from app.cloud_platform.validator import CloudIssue


class CloudPlatformError(QuantForgeError):
    """Base class for all Cloud Platform errors."""


class CloudConfigurationError(CloudPlatformError):
    """Raised for an invalid `CloudPlatformContext`."""


class CloudValidationError(CloudPlatformError):
    """Raised when a workspace context fails pre-compile validation.

    Carries the full list of `CloudIssue`s for a complete report.
    """

    def __init__(self, issues: list["CloudIssue"]) -> None:
        self.issues = issues
        summary = "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
        super().__init__(f"Cloud workspace context failed validation: {summary}")


class CloudNotFoundError(CloudPlatformError):
    """Raised when a requested cloud build id isn't registered."""


class CloudDisabledError(CloudPlatformError):
    """Raised when a requested cloud build is registered but disabled."""


class CloudRegistrationError(CloudPlatformError):
    """Raised for duplicate or malformed cloud build registration."""
