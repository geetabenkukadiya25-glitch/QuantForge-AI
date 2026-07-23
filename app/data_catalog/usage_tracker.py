"""Pure lineage-building functions (Phase 17.5). No state, no I/O --
`DataCatalog.sync()` supplies already-fetched data from `DatasetManager`
and `JobManager` and this module turns it into `DatasetLineageEvent`s.

Two kinds of lineage, built differently:

- **Exact** (`inferred=False`): read straight from `DatasetManager`'s own
  audit log (`DatasetAuditEvent`) and version history (`DatasetVersion`)
  -- Imported/Validated/Archived/Restored/Deleted/Exported/Reindexed.
  Nothing here recomputes or duplicates that data, only relabels it.
- **Correlated** (`inferred=True`): `JobManager` records no dataset
  reference on a `Job`/`JobRecord` (confirmed -- no dashboard populates
  `Job.metadata`), and neither `JobManager` nor any dashboard may be
  modified to add one. Instead, `app.ui.components.dataset_picker`
  (a component we own) writes a `DatasetUsageContext(page_key,
  dataset_id, timestamp)` every time a page resolves a dataset.
  `correlate_job_lineage` joins that stream against job history by
  `owner_page` + nearest-preceding timestamp within a lookback window --
  a best-effort "this job most likely used this dataset" call, always
  surfaced to the UI with `inferred=True` so it is never confused with
  the exact, audit-log-backed events above.
"""

from datetime import datetime

from app.data_catalog.models import DatasetLineageEvent, DatasetUsageContext, LineageEventKind
from app.dataset_manager.models import DatasetAuditEvent, DatasetAuditEventType, DatasetVersion, DatasetVersionEventType
from app.job_manager.models import JobCategory, JobRecord

_AUDIT_KIND_MAP: dict[DatasetAuditEventType, LineageEventKind] = {
    DatasetAuditEventType.IMPORTED: LineageEventKind.IMPORTED,
    DatasetAuditEventType.REVALIDATED: LineageEventKind.VALIDATED,
    DatasetAuditEventType.ARCHIVED: LineageEventKind.ARCHIVED,
    DatasetAuditEventType.RESTORED: LineageEventKind.RESTORED,
    DatasetAuditEventType.DELETED: LineageEventKind.DELETED,
    DatasetAuditEventType.EXPORTED: LineageEventKind.EXPORTED,
}

_JOB_CATEGORY_MAP: dict[str, LineageEventKind] = {
    JobCategory.BACKTEST.value: LineageEventKind.USED_BY_BACKTEST,
    JobCategory.OPTIMIZATION.value: LineageEventKind.USED_BY_OPTIMIZATION,
    JobCategory.VALIDATION.value: LineageEventKind.USED_BY_VALIDATION,
    JobCategory.REPLAY.value: LineageEventKind.USED_BY_REPLAY,
    JobCategory.RESEARCH.value: LineageEventKind.USED_BY_RESEARCH,
    JobCategory.PORTFOLIO.value: LineageEventKind.USED_BY_PORTFOLIO,
}

_DEFAULT_LOOKBACK_SECONDS = 7200.0


def build_exact_lineage_from_audit(dataset_id: str, audit_events: list[DatasetAuditEvent]) -> list[DatasetLineageEvent]:
    events = []
    for audit_event in audit_events:
        kind = _AUDIT_KIND_MAP.get(audit_event.event_type)
        if kind is None:
            continue
        events.append(
            DatasetLineageEvent(dataset_id=dataset_id, kind=kind, timestamp=audit_event.timestamp, inferred=False, status="OK")
        )
    return events


def build_exact_lineage_from_versions(dataset_id: str, versions: list[DatasetVersion]) -> list[DatasetLineageEvent]:
    events = []
    for version in versions:
        if version.event_type != DatasetVersionEventType.REINDEXED:
            continue
        events.append(
            DatasetLineageEvent(dataset_id=dataset_id, kind=LineageEventKind.REINDEXED, timestamp=version.timestamp, inferred=False, status="OK")
        )
    return events


def correlate_job_lineage(
    job_records: list[JobRecord],
    usage_contexts: list[DatasetUsageContext],
    lookback_seconds: float = _DEFAULT_LOOKBACK_SECONDS,
) -> list[DatasetLineageEvent]:
    """For each finished/running job, find the most recent usage-context
    event on the same `owner_page` at or before the job's creation time
    (within `lookback_seconds`), and treat that as the dataset the job
    used. Jobs with no matching context (e.g. dashboards that don't
    consume a dataset) are silently skipped -- never fabricated."""
    contexts_by_page: dict[str, list[DatasetUsageContext]] = {}
    for ctx in usage_contexts:
        contexts_by_page.setdefault(ctx.page_key, []).append(ctx)
    for contexts in contexts_by_page.values():
        contexts.sort(key=lambda c: c.timestamp)

    events: list[DatasetLineageEvent] = []
    for job in job_records:
        kind = _JOB_CATEGORY_MAP.get(job.category)
        if kind is None:
            continue
        try:
            job_time = datetime.fromisoformat(job.created_at)
        except ValueError:
            continue

        best: DatasetUsageContext | None = None
        for ctx in contexts_by_page.get(job.owner_page, []):
            if ctx.timestamp > job_time:
                continue
            if (job_time - ctx.timestamp).total_seconds() > lookback_seconds:
                continue
            if best is None or ctx.timestamp > best.timestamp:
                best = ctx
        if best is None:
            continue

        events.append(
            DatasetLineageEvent(
                dataset_id=best.dataset_id,
                kind=kind,
                timestamp=job_time,
                inferred=True,
                job_id=job.id,
                owner_page=job.owner_page,
                status=job.state,
                label=job.name,
            )
        )
    return events
