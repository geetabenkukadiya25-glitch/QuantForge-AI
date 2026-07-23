"""`app.data_catalog.models` -- round-trip `to_dict`/`from_dict` for every
persisted dataclass."""

from datetime import datetime, timezone

from app.data_catalog.models import (
    CatalogAuditEvent,
    CatalogAuditEventType,
    CatalogOverlay,
    DataCatalogState,
    DatasetLineageEvent,
    DatasetUsageContext,
    LineageEventKind,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_catalog_overlay_round_trip() -> None:
    overlay = CatalogOverlay(dataset_id="abc", owner="Alice", catalog_notes="Reviewed quarterly")
    assert CatalogOverlay.from_dict(overlay.to_dict()) == overlay


def test_dataset_lineage_event_round_trip() -> None:
    event = DatasetLineageEvent(
        dataset_id="abc", kind=LineageEventKind.USED_BY_BACKTEST, timestamp=NOW, inferred=True,
        job_id="job1", owner_page="Backtesting Dashboard", status="COMPLETED", label="Backtest: EMA",
    )
    assert DatasetLineageEvent.from_dict(event.to_dict()) == event


def test_dataset_usage_context_round_trip() -> None:
    ctx = DatasetUsageContext(page_key="backtesting", dataset_id="abc", timestamp=NOW)
    assert DatasetUsageContext.from_dict(ctx.to_dict()) == ctx


def test_catalog_audit_event_round_trip() -> None:
    event = CatalogAuditEvent(event_type=CatalogAuditEventType.REFERENCED, key="abc", timestamp=NOW)
    assert CatalogAuditEvent.from_dict(event.to_dict()) == event


def test_data_catalog_state_round_trip() -> None:
    state = DataCatalogState(
        records={"abc": CatalogOverlay(dataset_id="abc", owner="Alice")},
        usage_contexts=[DatasetUsageContext(page_key="backtesting", dataset_id="abc", timestamp=NOW)],
        lineage_events={"abc": [DatasetLineageEvent(dataset_id="abc", kind=LineageEventKind.IMPORTED, timestamp=NOW, inferred=False)]},
    )
    restored = DataCatalogState.from_dict(state.to_dict())
    assert restored.records == state.records
    assert restored.usage_contexts == state.usage_contexts
    assert restored.lineage_events == state.lineage_events
