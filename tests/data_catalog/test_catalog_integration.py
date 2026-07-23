"""`app.data_catalog.DataCatalog` integration test -- register a dataset
via `DatasetManager`, simulate a usage-context observation plus a
correlated job-history entry, run `sync()`, and assert lineage/usage-
stats/dependency-tree/impact all reflect it. Also covers the exact
(non-inferred) lineage path via Dataset Manager's own audit/version
events, and the owner/catalog-notes overlay."""

from datetime import datetime, timedelta, timezone

from app.data_catalog.catalog import DataCatalog
from app.data_catalog.models import LineageEventKind
from app.dataset_manager.dataset_manager import DatasetManager
from app.job_manager.job_history import JobHistoryStore
from app.job_manager.models import JobRecord

def _seed_backtest_job(job_history_dir, dataset_id: str, catalog: DataCatalog, page_key: str = "backtesting") -> None:
    catalog.record_usage_context(page_key, dataset_id)
    # `job_time` must be computed fresh, after `record_usage_context`'s own
    # `datetime.now(...)` call, and comfortably after it -- otherwise a
    # module-level "now" captured at collection time can end up BEFORE the
    # usage-context timestamp once other tests have consumed real wall-clock
    # time, breaking the "usage context <= job creation time" correlation.
    job_time = datetime.now(timezone.utc) + timedelta(seconds=5)
    record = JobRecord(
        id="job-1", name="Backtest: EMA Crossover", category="BACKTEST", state="COMPLETED", owner_page=page_key,
        created_at=job_time.isoformat(), started_at=job_time.isoformat(), ended_at=(job_time + timedelta(seconds=5)).isoformat(),
        elapsed_seconds=5.0, error_message=None,
    )
    JobHistoryStore(job_history_dir).record(record)


def test_exact_lineage_comes_from_dataset_manager_audit_and_versions(catalog: DataCatalog, dataset_manager: DatasetManager, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    dataset_manager.reindex(record.id)
    dataset_manager.revalidate(record.id)

    catalog.sync()
    lineage = catalog.lineage(record.id)
    kinds = {e.kind for e in lineage}
    assert LineageEventKind.IMPORTED in kinds
    assert LineageEventKind.REINDEXED in kinds
    assert LineageEventKind.VALIDATED in kinds
    assert all(not e.inferred for e in lineage)


def test_inferred_lineage_correlates_job_to_dataset(catalog: DataCatalog, dataset_manager: DatasetManager, job_history_dir, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    _seed_backtest_job(job_history_dir, record.id, catalog)

    catalog.sync()
    lineage = catalog.lineage(record.id)
    used_by = [e for e in lineage if e.kind == LineageEventKind.USED_BY_BACKTEST]
    assert len(used_by) == 1
    assert used_by[0].inferred is True
    assert used_by[0].job_id == "job-1"
    assert used_by[0].status == "COMPLETED"


def test_dependency_tree_and_usage_stats_reflect_synced_lineage(catalog: DataCatalog, dataset_manager: DatasetManager, job_history_dir, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    _seed_backtest_job(job_history_dir, record.id, catalog)
    catalog.sync()

    tree = catalog.dependency_tree(record.id)
    assert tree.label == record.display_name
    assert len(tree.children) == 1

    usage = catalog.usage_stats(record.id)
    assert usage.times_used == 1
    assert usage.completed_jobs == 1


def test_impact_never_blocks_and_reports_reference_counts(catalog: DataCatalog, dataset_manager: DatasetManager, job_history_dir, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    _seed_backtest_job(job_history_dir, record.id, catalog)
    catalog.sync()

    impact = catalog.impact(record.id)
    assert impact["backtests"] == 1
    assert impact["total_references"] == 1

    # Archive/delete are never blocked by the catalog -- it only reports.
    dataset_manager.archive(record.id)
    assert dataset_manager.get(record.id).archived is True


def test_owner_and_catalog_notes_overlay(catalog: DataCatalog, dataset_manager: DatasetManager, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    catalog.set_owner(record.id, "Quant Desk")
    catalog.set_catalog_notes(record.id, "Primary EURUSD source")

    entry = catalog.get(record.id)
    assert entry.owner == "Quant Desk"
    assert entry.display_name == record.display_name  # still sourced live from DatasetManager


def test_search_and_filter_over_catalog(catalog: DataCatalog, dataset_manager: DatasetManager, valid_csv_bytes: bytes) -> None:
    record = dataset_manager.import_dataset_from_bytes(valid_csv_bytes, filename="EURUSD_H1.csv")
    catalog.set_owner(record.id, "Quant Desk")

    assert [e.id for e in catalog.search("Quant Desk")] == [record.id]
    assert [e.id for e in catalog.filter_entries(favorite=False)] == [record.id]
