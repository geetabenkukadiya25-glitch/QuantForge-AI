from pathlib import Path

from app.job_manager.job_history import JobHistoryStore
from app.job_manager.models import JobRecord


def _record(job_id: str = "abc") -> JobRecord:
    return JobRecord(
        id=job_id, name="Test Job", category="BACKTEST", state="COMPLETED", owner_page="Backtesting Dashboard",
        created_at="2026-01-01T00:00:00+00:00", started_at="2026-01-01T00:00:01+00:00", ended_at="2026-01-01T00:00:02+00:00",
        elapsed_seconds=1.0, error_message=None, metadata={},
    )


def test_record_and_list(tmp_path: Path):
    store = JobHistoryStore(tmp_path)
    store.record(_record("a"))
    store.record(_record("b"))
    records = store.list_records()
    assert {r.id for r in records} == {"a", "b"}


def test_list_records_empty_when_no_file(tmp_path: Path):
    store = JobHistoryStore(tmp_path)
    assert store.list_records() == []


def test_list_records_degrades_gracefully_on_corrupt_file(tmp_path: Path):
    store = JobHistoryStore(tmp_path)
    store.record(_record("a"))
    (tmp_path / "jobs_history.jsonl").write_text("not valid json\n", encoding="utf-8")
    assert store.list_records() == []


def test_trim_keeps_most_recent(tmp_path: Path, monkeypatch):
    import app.job_manager.job_history as job_history_module

    monkeypatch.setattr(job_history_module, "_MAX_RECORDS", 3)
    store = JobHistoryStore(tmp_path)
    for i in range(5):
        store.record(_record(f"job-{i}"))
    records = store.list_records(limit=10)
    assert len(records) == 3
    assert {r.id for r in records} == {"job-2", "job-3", "job-4"}
