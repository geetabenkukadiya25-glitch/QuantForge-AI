"""Exceptions for the Job Manager (Phase 18.4).

Presentation/orchestration-layer only -- these are never raised by, or
caught inside, any trading/SDL/engine module.
"""


class JobManagerError(Exception):
    """Base class for all Job Manager errors."""


class JobNotFoundError(JobManagerError):
    """Raised when a job id does not exist in the manager's registry."""


class JobCancelledError(JobManagerError):
    """Raised from inside a progress callback to cooperatively unwind a
    running operation whose owning job has been cancel-requested. Only
    meaningful for operations that invoke the callback the Job Manager
    handed them -- engines with no progress callback cannot be
    interrupted this way, and this is never used to forcibly kill a
    thread."""
