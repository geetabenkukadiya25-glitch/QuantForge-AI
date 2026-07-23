"""Data models for the MT5 Live Data Synchronization Engine (Phase
19.2). Pure data -- manual `to_dict`/`from_dict` on every dataclass,
mirroring the idiom already used throughout `app.mt5.mt5_models`.
Nothing here performs I/O.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any


class SyncKind(str, Enum):
    SYMBOL = "SYMBOL"
    TICK = "TICK"
    BAR = "BAR"
    MARKET_WATCH = "MARKET_WATCH"
    MARKET_BOOK = "MARKET_BOOK"
    SPREAD = "SPREAD"
    SESSION = "SESSION"


class SyncStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class SyncRun:
    """One record of a single synchronization attempt -- how many
    records were synced, how long it took, and whether it succeeded.
    Never carries the synced data itself (that stays with the caller /
    goes to the bridge) -- this is bookkeeping only."""

    kind: SyncKind
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: SyncStatus = SyncStatus.PENDING
    target: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now())
    completed_at: datetime | None = None
    records_synced: int = 0
    latency_ms: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "status": self.status.value,
            "target": self.target,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "records_synced": self.records_synced,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SyncRun":
        completed_at = data.get("completed_at")
        return SyncRun(
            id=data.get("id", uuid.uuid4().hex),
            kind=SyncKind(data["kind"]),
            status=SyncStatus(data.get("status", SyncStatus.PENDING.value)),
            target=data.get("target", ""),
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            records_synced=data.get("records_synced", 0),
            latency_ms=data.get("latency_ms"),
            error=data.get("error"),
        )


@dataclass(frozen=True)
class SessionWindow:
    """One standard FX trading session window, computed purely from
    fixed UTC hour ranges -- no MT5 call, no broker-specific data."""

    name: str
    utc_open: time
    utc_close: time
    is_active: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "utc_open": self.utc_open.isoformat(),
            "utc_close": self.utc_close.isoformat(),
            "is_active": self.is_active,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SessionWindow":
        return SessionWindow(
            name=data["name"],
            utc_open=time.fromisoformat(data["utc_open"]),
            utc_close=time.fromisoformat(data["utc_close"]),
            is_active=data["is_active"],
        )


@dataclass(frozen=True)
class SpreadSample:
    """One point-in-time spread reading, derived from an existing
    `market_watch.get_quote()` result -- no new MT5 call."""

    symbol: str
    spread: float
    bid: float
    ask: float
    sampled_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "spread": self.spread,
            "bid": self.bid,
            "ask": self.ask,
            "sampled_at": self.sampled_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SpreadSample":
        return SpreadSample(
            symbol=data["symbol"],
            spread=data["spread"],
            bid=data["bid"],
            ask=data["ask"],
            sampled_at=datetime.fromisoformat(data["sampled_at"]),
        )
