"""Job categories and the JSON-serializable job history record (Phase 18.4).

Pure data -- no engine imports. `JobRecord` is what actually gets
persisted to `app/runtime/jobs/jobs_history.jsonl`; it never holds the
job's `operation` callable or its full (possibly large/non-serializable)
`result`, only a small descriptive snapshot.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class JobCategory(str, Enum):
    BACKTEST = "BACKTEST"
    OPTIMIZATION = "OPTIMIZATION"
    REPLAY = "REPLAY"
    VALIDATION = "VALIDATION"
    RESEARCH = "RESEARCH"
    EXTRACTION = "EXTRACTION"
    PORTFOLIO = "PORTFOLIO"
    EA_GENERATION = "EA_GENERATION"
    AI_ANALYSIS = "AI_ANALYSIS"
    KNOWLEDGE_INDEX = "KNOWLEDGE_INDEX"
    OTHER = "OTHER"


@dataclass(frozen=True)
class JobRecord:
    """A JSON-serializable snapshot of a finished job, for history."""

    id: str
    name: str
    category: str
    state: str
    owner_page: str
    created_at: str
    started_at: str | None
    ended_at: str | None
    elapsed_seconds: float | None
    error_message: str | None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "state": self.state,
            "owner_page": self.owner_page,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_seconds": self.elapsed_seconds,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "JobRecord":
        return JobRecord(
            id=data["id"],
            name=data["name"],
            category=data["category"],
            state=data["state"],
            owner_page=data["owner_page"],
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            ended_at=data.get("ended_at"),
            elapsed_seconds=data.get("elapsed_seconds"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )
