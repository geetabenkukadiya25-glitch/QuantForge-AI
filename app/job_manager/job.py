"""The `Job` object (Phase 18.4) -- pure orchestration state, no engine
imports. `operation` is an opaque callable a page provides; the Job
Manager never inspects or modifies what it does.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from app.job_manager.job_progress import JobProgress
from app.job_manager.job_state import JobState
from app.job_manager.models import JobCategory, JobRecord


@dataclass
class Job:
    name: str
    category: JobCategory
    owner_page: str
    operation: Callable[["Job"], Any]
    progress: JobProgress
    metadata: dict[str, Any] = field(default_factory=dict)

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state: JobState = JobState.QUEUED
    result: Any = None
    error: str | None = None
    cancel_requested: bool = False

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None

    @property
    def elapsed_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.ended_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    @property
    def eta_seconds(self) -> float | None:
        if self.state != JobState.RUNNING:
            return None
        return self.progress.estimated_remaining_seconds()

    def to_record(self) -> JobRecord:
        return JobRecord(
            id=self.id,
            name=self.name,
            category=self.category.value,
            state=self.state.value,
            owner_page=self.owner_page,
            created_at=self.created_at.isoformat(),
            started_at=self.started_at.isoformat() if self.started_at else None,
            ended_at=self.ended_at.isoformat() if self.ended_at else None,
            elapsed_seconds=self.elapsed_seconds,
            error_message=self.error,
            metadata={k: v for k, v in self.metadata.items() if isinstance(v, (str, int, float, bool, type(None)))},
        )
