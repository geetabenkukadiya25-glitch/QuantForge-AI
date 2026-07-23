"""`BridgeHealth` (Phase 19.1) -- reports on the JSON Bridge EXCHANGE
activity itself (export/import counts, last-validation status,
transport/checksum status). Distinct from the existing, Phase-19.0
`mt5_models.HealthSnapshot`, which reports terminal CONNECTION health
(latency/uptime/heartbeat) -- the two measure different things, so
neither duplicates the other. Pure aggregation, no I/O of its own; the
caller (`bridge_exchange_manager.py`) supplies the counters it already
tracks.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BridgeHealth:
    bridge_version: str
    schema_version: str
    payload_count: int
    export_count: int
    import_count: int
    last_export_at: datetime | None
    last_import_at: datetime | None
    last_validation_at: datetime | None
    last_validation_ok: bool | None
    transport_status: str
    checksum_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "bridge_version": self.bridge_version,
            "schema_version": self.schema_version,
            "payload_count": self.payload_count,
            "export_count": self.export_count,
            "import_count": self.import_count,
            "last_export_at": self.last_export_at.isoformat() if self.last_export_at else None,
            "last_import_at": self.last_import_at.isoformat() if self.last_import_at else None,
            "last_validation_at": self.last_validation_at.isoformat() if self.last_validation_at else None,
            "last_validation_ok": self.last_validation_ok,
            "transport_status": self.transport_status,
            "checksum_status": self.checksum_status,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BridgeHealth":
        def _opt_dt(key: str) -> datetime | None:
            value = data.get(key)
            return datetime.fromisoformat(value) if value else None

        return BridgeHealth(
            bridge_version=data.get("bridge_version", ""),
            schema_version=data.get("schema_version", ""),
            payload_count=data.get("payload_count", 0),
            export_count=data.get("export_count", 0),
            import_count=data.get("import_count", 0),
            last_export_at=_opt_dt("last_export_at"),
            last_import_at=_opt_dt("last_import_at"),
            last_validation_at=_opt_dt("last_validation_at"),
            last_validation_ok=data.get("last_validation_ok"),
            transport_status=data.get("transport_status", ""),
            checksum_status=data.get("checksum_status", ""),
        )


def build_bridge_health(
    *,
    bridge_version: str,
    schema_version: str,
    export_count: int,
    import_count: int,
    last_export_at: datetime | None,
    last_import_at: datetime | None,
    last_validation_at: datetime | None,
    last_validation_ok: bool | None,
    transport_available: bool,
    checksum_status: str,
) -> BridgeHealth:
    return BridgeHealth(
        bridge_version=bridge_version,
        schema_version=schema_version,
        payload_count=export_count + import_count,
        export_count=export_count,
        import_count=import_count,
        last_export_at=last_export_at,
        last_import_at=last_import_at,
        last_validation_at=last_validation_at,
        last_validation_ok=last_validation_ok,
        transport_status="not implemented" if not transport_available else "available",
        checksum_status=checksum_status,
    )
