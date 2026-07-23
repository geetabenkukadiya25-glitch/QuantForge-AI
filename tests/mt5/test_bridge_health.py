"""`bridge_health.py` -- pure aggregation + round-trip."""

from app.mt5.bridge_health import BridgeHealth, build_bridge_health


def test_build_bridge_health_sums_payload_count() -> None:
    health = build_bridge_health(
        bridge_version="1.0.0",
        schema_version="1.0.0",
        export_count=3,
        import_count=2,
        last_export_at=None,
        last_import_at=None,
        last_validation_at=None,
        last_validation_ok=None,
        transport_available=False,
        checksum_status="active",
    )
    assert health.payload_count == 5
    assert health.transport_status == "not implemented"


def test_build_bridge_health_transport_available_true() -> None:
    health = build_bridge_health(
        bridge_version="1.0.0",
        schema_version="1.0.0",
        export_count=0,
        import_count=0,
        last_export_at=None,
        last_import_at=None,
        last_validation_at=None,
        last_validation_ok=None,
        transport_available=True,
        checksum_status="not yet used",
    )
    assert health.transport_status == "available"


def test_bridge_health_round_trip() -> None:
    health = BridgeHealth(
        bridge_version="1.0.0",
        schema_version="1.0.0",
        payload_count=5,
        export_count=3,
        import_count=2,
        last_export_at=None,
        last_import_at=None,
        last_validation_at=None,
        last_validation_ok=True,
        transport_status="not implemented",
        checksum_status="active",
    )
    assert BridgeHealth.from_dict(health.to_dict()) == health
