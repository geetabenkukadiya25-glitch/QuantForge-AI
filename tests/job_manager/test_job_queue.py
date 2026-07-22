from app.job_manager.job_queue import JobQueue


def test_push_and_pop_fifo_order():
    queue = JobQueue()
    queue.push("a")
    queue.push("b")
    assert queue.pop_blocking(timeout=1) == "a"
    assert queue.pop_blocking(timeout=1) == "b"


def test_pop_blocking_times_out_when_empty():
    queue = JobQueue()
    assert queue.pop_blocking(timeout=0.05) is None


def test_remove_present_item():
    queue = JobQueue()
    queue.push("a")
    queue.push("b")
    assert queue.remove("a") is True
    assert queue.snapshot() == ["b"]


def test_remove_absent_item_returns_false():
    queue = JobQueue()
    assert queue.remove("missing") is False


def test_len_and_snapshot():
    queue = JobQueue()
    queue.push("a")
    queue.push("b")
    assert len(queue) == 2
    assert queue.snapshot() == ["a", "b"]
