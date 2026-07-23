"""Workflow settings section (Phase 18.8). `WorkflowStep.timeout`/
`retry_count` are today per-step attributes, not global engine knobs
(confirmed absent in the reuse audit); this section stores the intended
*default* values a user wants new steps to start with -- it does not
rewire `app.workflow` to read them (see Known Limitations)."""

from app.settings_center.settings_models import WorkflowSettings


def defaults() -> WorkflowSettings:
    return WorkflowSettings(retry_count=0, timeout_seconds=0.0, parallel_jobs=1, queue_size=0)


def validate(settings: WorkflowSettings) -> list[str]:
    issues = []
    if settings.retry_count < 0:
        issues.append("retry_count must be >= 0")
    if settings.timeout_seconds < 0:
        issues.append("timeout_seconds must be >= 0")
    if settings.parallel_jobs < 1:
        issues.append("parallel_jobs must be >= 1")
    if settings.queue_size < 0:
        issues.append("queue_size must be >= 0")
    return issues
