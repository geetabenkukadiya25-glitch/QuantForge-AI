"""`sync_statistics.py`/`sync_health.py` -- pure aggregation + persisted
counters round-trip."""

from datetime import datetime
from pathlib import Path

from app.mt5_sync.sync_health import build_sync_health
from app.mt5_sync.sync_models import SyncKind, SyncRun, SyncStatus
from app.mt5_sync.sync_statistics import SyncStatistics, SyncStatisticsStore


def test_statistics_record_updates_counts() -> None:
    stats = SyncStatistics()
    stats.record(SyncRun(kind=SyncKind.TICK, status=SyncStatus.COMPLETED, latency_ms=10.0))
    stats.record(SyncRun(kind=SyncKind.TICK, status=SyncStatus.FAILED, latency_ms=5.0))
    assert stats.total_runs == 2
    assert stats.success_count == 1
    assert stats.failure_count == 1
    assert stats.runs_by_kind == {"TICK": 2}
    assert stats.average_latency_ms == 7.5


def test_statistics_average_latency_zero_when_no_runs() -> None:
    assert SyncStatistics().average_latency_ms == 0.0


def test_statistics_round_trip() -> None:
    stats = SyncStatistics()
    stats.record(SyncRun(kind=SyncKind.BAR, status=SyncStatus.COMPLETED, latency_ms=2.0, completed_at=datetime(2026, 1, 1)))
    assert SyncStatistics.from_dict(stats.to_dict()) == stats


def test_statistics_store_persists(tmp_path: Path) -> None:
    store = SyncStatisticsStore(tmp_path)
    stats = SyncStatistics()
    stats.record(SyncRun(kind=SyncKind.SYMBOL, status=SyncStatus.COMPLETED, latency_ms=1.0))
    store.save(stats)
    reloaded = store.load()
    assert reloaded.total_runs == 1


def test_statistics_store_missing_file_returns_defaults(tmp_path: Path) -> None:
    store = SyncStatisticsStore(tmp_path / "nonexistent")
    assert store.load() == SyncStatistics()


def test_build_sync_health_unknown_when_no_runs() -> None:
    health = build_sync_health(SyncStatistics(), {}, {}, "DISCONNECTED")
    assert health.overall_status == "unknown"


def test_build_sync_health_healthy_when_no_failures() -> None:
    stats = SyncStatistics()
    run = SyncRun(kind=SyncKind.TICK, status=SyncStatus.COMPLETED, records_synced=5, completed_at=datetime.now())
    stats.record(run)
    health = build_sync_health(stats, {"TICK": run}, {}, "CONNECTED")
    assert health.overall_status == "healthy"
    assert len(health.per_kind) == 1
    assert health.per_kind[0].kind == "TICK"


def test_build_sync_health_degraded_when_failures_present() -> None:
    stats = SyncStatistics()
    run = SyncRun(kind=SyncKind.TICK, status=SyncStatus.FAILED, completed_at=datetime.now())
    stats.record(run)
    health = build_sync_health(stats, {"TICK": run}, {"TICK": 1}, "CONNECTED")
    assert health.overall_status == "degraded"
    assert health.per_kind[0].failure_count == 1
