from app.job_manager.job_events import JobEventLog


def test_append_and_events_since():
    log = JobEventLog()
    e1 = log.append("job-1", "started", "Job started.")
    e2 = log.append("job-1", "completed", "Job completed.")
    assert log.events_since(0) == [e1, e2]
    assert log.events_since(e1.id) == [e2]
    assert log.events_since(e2.id) == []


def test_latest_id():
    log = JobEventLog()
    assert log.latest_id == 0
    e1 = log.append("job-1", "started", "Job started.")
    assert log.latest_id == e1.id


def test_events_since_filters_only_newer_ids():
    log = JobEventLog()
    log.append("job-1", "started", "a")
    log.append("job-2", "started", "b")
    log.append("job-1", "completed", "c")
    all_events = log.events_since(0)
    job1_events = [e for e in all_events if e.job_id == "job-1"]
    assert len(job1_events) == 2
