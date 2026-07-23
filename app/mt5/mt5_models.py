"""Data models for the MT5 Integration Layer (Phase 19.0). Pure data --
`ConnectionState` + its transition map mirrors
`app.governance.governance_models.GovernanceStatus` exactly; every
dataclass below has a manual `to_dict`/`from_dict`, mirroring
`app.cloud_sync.cloud_models`. Nothing here performs I/O.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ConnectionState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    LOST = "LOST"
    RECONNECTING = "RECONNECTING"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    TERMINAL_NOT_RUNNING = "TERMINAL_NOT_RUNNING"
    PERMISSION_DENIED = "PERMISSION_DENIED"


# Legal `ConnectionState` transitions -- enforced by `connection_manager.py`.
# CONNECTED is only ever reached from CONNECTING, and only after a real,
# successful `MetaTrader5.initialize()` call -- there is no transition
# into CONNECTED from any other state, so a fabricated "connected"
# result is structurally impossible to reach through this map.
_TRANSITIONS: dict[ConnectionState, frozenset[ConnectionState]] = {
    ConnectionState.DISCONNECTED: frozenset({
        ConnectionState.CONNECTING,
    }),
    ConnectionState.CONNECTING: frozenset({
        ConnectionState.CONNECTED,
        ConnectionState.TERMINAL_NOT_RUNNING,
        ConnectionState.PERMISSION_DENIED,
        ConnectionState.UNSUPPORTED_VERSION,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.CONNECTED: frozenset({
        ConnectionState.DISCONNECTED,
        ConnectionState.LOST,
    }),
    ConnectionState.LOST: frozenset({
        ConnectionState.RECONNECTING,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.RECONNECTING: frozenset({
        ConnectionState.CONNECTED,
        ConnectionState.TERMINAL_NOT_RUNNING,
        ConnectionState.PERMISSION_DENIED,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.UNSUPPORTED_VERSION: frozenset({
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.TERMINAL_NOT_RUNNING: frozenset({
        ConnectionState.CONNECTING,
        ConnectionState.DISCONNECTED,
    }),
    ConnectionState.PERMISSION_DENIED: frozenset({
        ConnectionState.DISCONNECTED,
    }),
}


def is_valid_transition(from_state: ConnectionState, to_state: ConnectionState) -> bool:
    return to_state in _TRANSITIONS.get(from_state, frozenset())


@dataclass(frozen=True)
class TerminalInfo:
    """Read-only snapshot of `MetaTrader5.terminal_info()`."""

    community_account: bool
    connected: bool
    trade_allowed: bool
    trade_expert: bool
    build: int
    name: str
    company: str
    path: str
    data_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "community_account": self.community_account,
            "connected": self.connected,
            "trade_allowed": self.trade_allowed,
            "trade_expert": self.trade_expert,
            "build": self.build,
            "name": self.name,
            "company": self.company,
            "path": self.path,
            "data_path": self.data_path,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "TerminalInfo":
        return TerminalInfo(
            community_account=data.get("community_account", False),
            connected=data.get("connected", False),
            trade_allowed=data.get("trade_allowed", False),
            trade_expert=data.get("trade_expert", False),
            build=data.get("build", 0),
            name=data.get("name", ""),
            company=data.get("company", ""),
            path=data.get("path", ""),
            data_path=data.get("data_path", ""),
        )


@dataclass(frozen=True)
class AccountInfo:
    """Read-only snapshot of `MetaTrader5.account_info()`. Reporting
    only -- nothing in this package ever acts on these values."""

    login: int
    server: str
    currency: str
    balance: float
    equity: float
    margin: float
    margin_free: float
    leverage: int
    trade_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "login": self.login,
            "server": self.server,
            "currency": self.currency,
            "balance": self.balance,
            "equity": self.equity,
            "margin": self.margin,
            "margin_free": self.margin_free,
            "leverage": self.leverage,
            "trade_allowed": self.trade_allowed,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "AccountInfo":
        return AccountInfo(
            login=data.get("login", 0),
            server=data.get("server", ""),
            currency=data.get("currency", ""),
            balance=data.get("balance", 0.0),
            equity=data.get("equity", 0.0),
            margin=data.get("margin", 0.0),
            margin_free=data.get("margin_free", 0.0),
            leverage=data.get("leverage", 0),
            trade_allowed=data.get("trade_allowed", False),
        )


@dataclass(frozen=True)
class SymbolInfo:
    """Read-only snapshot of one `MetaTrader5.symbol_info()` result."""

    name: str
    description: str
    path: str
    digits: int
    point: float
    visible: bool
    spread: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "path": self.path,
            "digits": self.digits,
            "point": self.point,
            "visible": self.visible,
            "spread": self.spread,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "SymbolInfo":
        return SymbolInfo(
            name=data.get("name", ""),
            description=data.get("description", ""),
            path=data.get("path", ""),
            digits=data.get("digits", 0),
            point=data.get("point", 0.0),
            visible=data.get("visible", False),
            spread=data.get("spread", 0),
        )


@dataclass(frozen=True)
class Bar:
    """One read-only OHLCV bar from `MetaTrader5.copy_rates_*`."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "tick_volume": self.tick_volume,
            "spread": self.spread,
            "real_volume": self.real_volume,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Bar":
        return Bar(
            time=datetime.fromisoformat(data["time"]),
            open=data.get("open", 0.0),
            high=data.get("high", 0.0),
            low=data.get("low", 0.0),
            close=data.get("close", 0.0),
            tick_volume=data.get("tick_volume", 0),
            spread=data.get("spread", 0),
            real_volume=data.get("real_volume", 0),
        )


@dataclass(frozen=True)
class Tick:
    """One read-only tick from `MetaTrader5.copy_ticks_*`."""

    time: datetime
    bid: float
    ask: float
    last: float
    volume: int
    flags: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "volume": self.volume,
            "flags": self.flags,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Tick":
        return Tick(
            time=datetime.fromisoformat(data["time"]),
            bid=data.get("bid", 0.0),
            ask=data.get("ask", 0.0),
            last=data.get("last", 0.0),
            volume=data.get("volume", 0),
            flags=data.get("flags", 0),
        )


@dataclass
class HealthSnapshot:
    """Aggregated health metrics, built by `terminal_health.py` from the
    other managers' state -- never a source of new I/O itself."""

    connection_state: ConnectionState
    latency_ms: float | None
    connection_uptime_seconds: float | None
    last_heartbeat_at: datetime | None
    last_tick_at: datetime | None
    last_history_sync_at: datetime | None
    last_ping_at: datetime | None
    terminal_build: int | None
    bridge_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_state": self.connection_state.value,
            "latency_ms": self.latency_ms,
            "connection_uptime_seconds": self.connection_uptime_seconds,
            "last_heartbeat_at": self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None,
            "last_tick_at": self.last_tick_at.isoformat() if self.last_tick_at else None,
            "last_history_sync_at": self.last_history_sync_at.isoformat() if self.last_history_sync_at else None,
            "last_ping_at": self.last_ping_at.isoformat() if self.last_ping_at else None,
            "terminal_build": self.terminal_build,
            "bridge_version": self.bridge_version,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "HealthSnapshot":
        def _opt_dt(key: str) -> datetime | None:
            value = data.get(key)
            return datetime.fromisoformat(value) if value else None

        return HealthSnapshot(
            connection_state=ConnectionState(data["connection_state"]),
            latency_ms=data.get("latency_ms"),
            connection_uptime_seconds=data.get("connection_uptime_seconds"),
            last_heartbeat_at=_opt_dt("last_heartbeat_at"),
            last_tick_at=_opt_dt("last_tick_at"),
            last_history_sync_at=_opt_dt("last_history_sync_at"),
            last_ping_at=_opt_dt("last_ping_at"),
            terminal_build=data.get("terminal_build"),
            bridge_version=data.get("bridge_version", ""),
        )


@dataclass
class MT5ManagerState:
    """The small piece of persisted state this package keeps: the last
    known connection state (for UI continuity across reruns/restarts,
    never used to fabricate a live connection) and local, non-Settings-
    Center MT5 preferences."""

    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    auto_connect: bool = False
    retry_interval_seconds: int = 30
    terminal_path_override: str | None = None
    connected_since: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "connection_state": self.connection_state.value,
            "auto_connect": self.auto_connect,
            "retry_interval_seconds": self.retry_interval_seconds,
            "terminal_path_override": self.terminal_path_override,
            "connected_since": self.connected_since.isoformat() if self.connected_since else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "MT5ManagerState":
        connected_since = data.get("connected_since")
        return MT5ManagerState(
            connection_state=ConnectionState(data.get("connection_state", ConnectionState.DISCONNECTED.value)),
            auto_connect=data.get("auto_connect", False),
            retry_interval_seconds=data.get("retry_interval_seconds", 30),
            terminal_path_override=data.get("terminal_path_override"),
            connected_since=datetime.fromisoformat(connected_since) if connected_since else None,
        )


# ----------------------------------------------------------------------
# Phase 19.1 additions -- appended, nothing above this line changed.
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class PositionInfo:
    """Read-only snapshot of one `MetaTrader5.positions_get()` result.
    Reporting only -- nothing in this package ever closes or modifies a
    position; there is no such function anywhere in `app.mt5`."""

    ticket: int
    symbol: str
    type: int  # 0 = buy, 1 = sell (MetaTrader5.POSITION_TYPE_*)
    volume: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    profit: float
    swap: float
    time: datetime
    magic: int
    comment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.type,
            "volume": self.volume,
            "price_open": self.price_open,
            "sl": self.sl,
            "tp": self.tp,
            "price_current": self.price_current,
            "profit": self.profit,
            "swap": self.swap,
            "time": self.time.isoformat(),
            "magic": self.magic,
            "comment": self.comment,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "PositionInfo":
        return PositionInfo(
            ticket=data.get("ticket", 0),
            symbol=data.get("symbol", ""),
            type=data.get("type", 0),
            volume=data.get("volume", 0.0),
            price_open=data.get("price_open", 0.0),
            sl=data.get("sl", 0.0),
            tp=data.get("tp", 0.0),
            price_current=data.get("price_current", 0.0),
            profit=data.get("profit", 0.0),
            swap=data.get("swap", 0.0),
            time=datetime.fromisoformat(data["time"]),
            magic=data.get("magic", 0),
            comment=data.get("comment", ""),
        )


@dataclass(frozen=True)
class OrderInfo:
    """Read-only snapshot of one `MetaTrader5.orders_get()` (pending
    order) result. Reporting only -- nothing in this package ever
    places, modifies, or cancels an order."""

    ticket: int
    symbol: str
    type: int  # MetaTrader5.ORDER_TYPE_*
    state: int  # MetaTrader5.ORDER_STATE_*
    volume_current: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    time_setup: datetime
    magic: int
    comment: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket": self.ticket,
            "symbol": self.symbol,
            "type": self.type,
            "state": self.state,
            "volume_current": self.volume_current,
            "price_open": self.price_open,
            "sl": self.sl,
            "tp": self.tp,
            "price_current": self.price_current,
            "time_setup": self.time_setup.isoformat(),
            "magic": self.magic,
            "comment": self.comment,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OrderInfo":
        return OrderInfo(
            ticket=data.get("ticket", 0),
            symbol=data.get("symbol", ""),
            type=data.get("type", 0),
            state=data.get("state", 0),
            volume_current=data.get("volume_current", 0.0),
            price_open=data.get("price_open", 0.0),
            sl=data.get("sl", 0.0),
            tp=data.get("tp", 0.0),
            price_current=data.get("price_current", 0.0),
            time_setup=datetime.fromisoformat(data["time_setup"]),
            magic=data.get("magic", 0),
            comment=data.get("comment", ""),
        )


@dataclass
class BridgeExchangeState:
    """The small piece of persisted state `BridgeExchangeManager` keeps
    -- export/import counters and last-activity timestamps -- in its own
    file, deliberately separate from `MT5ManagerState`'s, so that
    dataclass's existing schema is never touched. (Phase 19.1, additive.)"""

    export_count: int = 0
    import_count: int = 0
    last_export_at: datetime | None = None
    last_import_at: datetime | None = None
    last_validation_at: datetime | None = None
    last_validation_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "export_count": self.export_count,
            "import_count": self.import_count,
            "last_export_at": self.last_export_at.isoformat() if self.last_export_at else None,
            "last_import_at": self.last_import_at.isoformat() if self.last_import_at else None,
            "last_validation_at": self.last_validation_at.isoformat() if self.last_validation_at else None,
            "last_validation_ok": self.last_validation_ok,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "BridgeExchangeState":
        def _opt_dt(key: str) -> datetime | None:
            value = data.get(key)
            return datetime.fromisoformat(value) if value else None

        return BridgeExchangeState(
            export_count=data.get("export_count", 0),
            import_count=data.get("import_count", 0),
            last_export_at=_opt_dt("last_export_at"),
            last_import_at=_opt_dt("last_import_at"),
            last_validation_at=_opt_dt("last_validation_at"),
            last_validation_ok=data.get("last_validation_ok"),
        )
