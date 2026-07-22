"""Job Manager (Phase 18.4) -- a central, process-wide orchestrator that
every dashboard submits its heavy operation to instead of calling an
engine directly.

Pure orchestration/presentation-adjacent infrastructure: nothing in this
package imports any trading/SDL/engine/database module. It accepts an
opaque `operation` callable per job and forwards progress into the
existing, unmodified `ProgressTracker` (`app.ui.progress`) -- it never
introduces a second progress system and never changes engine behavior.
"""

import threading

from app.config.paths import get_paths
from app.job_manager.exceptions import JobCancelledError, JobManagerError, JobNotFoundError
from app.job_manager.job import Job
from app.job_manager.job_manager import JobManager
from app.job_manager.job_state import JobState
from app.job_manager.models import JobCategory, JobRecord

__all__ = [
    "Job",
    "JobManager",
    "JobState",
    "JobCategory",
    "JobRecord",
    "JobManagerError",
    "JobNotFoundError",
    "JobCancelledError",
    "get_job_manager",
]

_singleton: JobManager | None = None
_singleton_lock = threading.Lock()


def get_job_manager() -> JobManager:
    """The process-wide `JobManager` singleton -- shared by every page
    and every Streamlit session in this process, which is what makes it
    a genuinely central job manager rather than a per-page one."""
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = JobManager(history_dir=get_paths().jobs_history_dir)
    return _singleton
