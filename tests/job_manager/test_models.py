from app.job_manager.models import JobCategory, JobRecord


def test_job_category_values():
    assert JobCategory.BACKTEST.value == "BACKTEST"
    assert JobCategory.KNOWLEDGE_INDEX.value == "KNOWLEDGE_INDEX"
    assert JobCategory.EA_GENERATION.value == "EA_GENERATION"


def test_job_record_round_trip():
    record = JobRecord(
        id="abc123",
        name="Test Job",
        category=JobCategory.BACKTEST.value,
        state="COMPLETED",
        owner_page="Backtesting Dashboard",
        created_at="2026-01-01T00:00:00+00:00",
        started_at="2026-01-01T00:00:01+00:00",
        ended_at="2026-01-01T00:00:02+00:00",
        elapsed_seconds=1.0,
        error_message=None,
        metadata={"choice": "sma_cross_executable"},
    )
    restored = JobRecord.from_dict(record.to_dict())
    assert restored == record


def test_job_record_from_dict_tolerates_missing_optional_fields():
    restored = JobRecord.from_dict(
        {
            "id": "x",
            "name": "n",
            "category": "BACKTEST",
            "state": "QUEUED",
            "owner_page": "p",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    )
    assert restored.started_at is None
    assert restored.ended_at is None
    assert restored.elapsed_seconds is None
    assert restored.error_message is None
    assert restored.metadata == {}
