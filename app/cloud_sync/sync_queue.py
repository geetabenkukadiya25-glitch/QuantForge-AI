"""Ordering helper over queued `SyncOperation`s (Phase 17.9). This is
NOT a durable store -- `SyncOperation` records already persist durably
via `sync_manager.py`'s own JSON state. `SyncQueue` only answers "what
order should QUEUED operations be considered in" and holds nothing on
disk itself. Nothing pops or dispatches from this queue automatically --
there is no worker thread anywhere in this package.
"""

from app.cloud_sync.cloud_models import SyncOperation, SyncOperationStatus


def ordered_queued(operations: dict[str, SyncOperation]) -> list[SyncOperation]:
    """Every QUEUED operation, oldest-first."""
    queued = [op for op in operations.values() if op.status == SyncOperationStatus.QUEUED]
    return sorted(queued, key=lambda op: op.created_at)


class SyncQueue:
    """A thin in-memory FIFO of operation ids, mirroring
    `app.workflow.workflow_queue.WorkflowQueue`'s shape for API
    familiarity -- unlike that queue, nothing ever blocks waiting to pop
    from this one, since no dispatcher thread exists to consume it."""

    def __init__(self) -> None:
        self._items: list[str] = []

    def push(self, operation_id: str) -> None:
        self._items.append(operation_id)

    def peek(self) -> str | None:
        return self._items[0] if self._items else None

    def remove(self, operation_id: str) -> bool:
        try:
            self._items.remove(operation_id)
        except ValueError:
            return False
        return True

    def snapshot(self) -> list[str]:
        return list(self._items)

    def size(self) -> int:
        return len(self._items)
