"""`app.data_catalog.usage_tracker` -- pure exact-lineage builders and the
job<->usage-context correlation logic, with synthetic fixtures (no real
`DatasetManager`/`JobManager` I/O)."""

from datetime import datetime, timedelta, timezone

from app.data_catalog.models import DatasetUsageContext, LineageEventKind
from app.data_catalog.usage_tracker import (
    build_exact_lineage_from_audit,
    build_exact_lineage_from_versions,
    correlate_job_lineage,
)
from app.dataset_manager.models import (
    DatasetAuditEvent,
    DatasetAuditEventType,
    DatasetVersion,
    DatasetVersionEventType,
)
from app.job_manager.models import JobRecord

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_build_exact_lineage_from_audit_maps_known_kinds() -> None:
    events = [
        DatasetAuditEvent(event_type=DatasetAuditEventType.IMPORTED, key="ds1", timestamp=NOW),
        DatasetAuditEvent(event_type=DatasetAuditEventType.REVALIDATED, key="ds1", timestamp=NOW),
        DatasetAuditEvent(event_type=DatasetAuditEventType.RENAMED, key="ds1", timestamp=NOW),
    ]
    lineage = build_exact_lineage_from_audit("ds1", events)
    kinds = {e.kind for e in lineage}
    assert kinds == {LineageEventKind.IMPORTED, LineageEventKind.VALIDATED}
    assert all(not e.inferred for e in lineage)


def test_build_exact_lineage_from_versions_only_keeps_reindexed() -> None:
    versions = [
        DatasetVersion(event_type=DatasetVersionEventType.REINDEXED, timestamp=NOW),
        DatasetVersion(event_type=DatasetVersionEventType.CREATED, timestamp=NOW),
    ]
    lineage = build_exact_lineage_from_versions("ds1", versions)
    assert len(lineage) == 1
    assert lineage[0].kind == LineageEventKind.REINDEXED
    assert lineage[0].inferred is False


def _job_record(job_id: str, category: str, owner_page: str, created_at: datetime, state: str = "COMPLETED") -> JobRecord:
    return JobRecord(
        id=job_id, name=f"{category.title()}: Test", category=category, state=state, owner_page=owner_page,
        created_at=created_at.isoformat(), started_at=created_at.isoformat(), ended_at=created_at.isoformat(),
        elapsed_seconds=5.0, error_message=None,
    )


def test_correlate_picks_nearest_preceding_usage_context_on_same_page() -> None:
    job = _job_record("j1", "BACKTEST", "Backtesting Dashboard", NOW)
    older_ctx = DatasetUsageContext(page_key="Backtesting Dashboard", dataset_id="ds_old", timestamp=NOW - timedelta(minutes=30))
    nearer_ctx = DatasetUsageContext(page_key="Backtesting Dashboard", dataset_id="ds_new", timestamp=NOW - timedelta(minutes=5))

    events = correlate_job_lineage([job], [older_ctx, nearer_ctx])
    assert len(events) == 1
    assert events[0].dataset_id == "ds_new"
    assert events[0].kind == LineageEventKind.USED_BY_BACKTEST
    assert events[0].inferred is True
    assert events[0].job_id == "j1"


def test_correlate_ignores_context_on_a_different_page() -> None:
    job = _job_record("j1", "BACKTEST", "Backtesting Dashboard", NOW)
    ctx = DatasetUsageContext(page_key="Optimization Dashboard", dataset_id="ds1", timestamp=NOW - timedelta(minutes=1))
    assert correlate_job_lineage([job], [ctx]) == []


def test_correlate_ignores_context_after_job_created(_now=NOW) -> None:
    job = _job_record("j1", "BACKTEST", "Backtesting Dashboard", NOW)
    future_ctx = DatasetUsageContext(page_key="Backtesting Dashboard", dataset_id="ds1", timestamp=NOW + timedelta(minutes=1))
    assert correlate_job_lineage([job], [future_ctx]) == []


def test_correlate_respects_lookback_window() -> None:
    job = _job_record("j1", "BACKTEST", "Backtesting Dashboard", NOW)
    stale_ctx = DatasetUsageContext(page_key="Backtesting Dashboard", dataset_id="ds1", timestamp=NOW - timedelta(hours=5))
    assert correlate_job_lineage([job], [stale_ctx], lookback_seconds=7200) == []


def test_correlate_skips_unmapped_job_categories() -> None:
    job = _job_record("j1", "KNOWLEDGE_INDEX", "Knowledge Base", NOW)
    ctx = DatasetUsageContext(page_key="Knowledge Base", dataset_id="ds1", timestamp=NOW - timedelta(minutes=1))
    assert correlate_job_lineage([job], [ctx]) == []
