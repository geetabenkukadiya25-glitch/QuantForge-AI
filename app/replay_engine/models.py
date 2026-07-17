"""Immutable models for the Replay Engine.

Every pydantic model here is `frozen=True` -- hashable and immutable by
construction, the same discipline every prior engine's artifacts use.
`ReplayResult` is the single artifact this engine produces: a
deterministic, versioned, serializable record of one replay preparation.
It never carries a broker handle, a live connection, or strategy-modifying
logic -- replay is read-only playback of already-computed history.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.replay_engine.metadata import ReplayMetadata


class ReplayEngineModel(BaseModel):
    """Base class for every replay_engine model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class PlaybackState(str, Enum):
    STOPPED = "STOPPED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"


class ReplaySpeed(float, Enum):
    """Supported playback speed multipliers.

    This engine has no real-time timer/thread of its own (a framework
    placeholder, like Phase 9's `latency_bars`) -- `speed` only governs how
    many frames `ReplayPlayer.auto_play_tick()` advances per call.
    `MAXIMUM` advances straight to the end in a single call, i.e. no
    per-step throttling at all.
    """

    X0_25 = 0.25
    X0_5 = 0.5
    X1 = 1.0
    X2 = 2.0
    X4 = 4.0
    X8 = 8.0
    MAXIMUM = -1.0


class ReplayEventType(str, Enum):
    REPLAY_STARTED = "REPLAY_STARTED"
    REPLAY_PAUSED = "REPLAY_PAUSED"
    REPLAY_RESUMED = "REPLAY_RESUMED"
    REPLAY_FINISHED = "REPLAY_FINISHED"
    FRAME_CHANGED = "FRAME_CHANGED"
    TRADE_OPENED = "TRADE_OPENED"
    TRADE_CLOSED = "TRADE_CLOSED"
    SIGNAL_CREATED = "SIGNAL_CREATED"


class ReplayConfiguration(ReplayEngineModel):
    """Configurable scope and default playback assumptions for one replay preparation."""

    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    default_speed: ReplaySpeed = ReplaySpeed.X1
    start_index: int = Field(ge=0, default=0)
    end_index: int | None = Field(default=None, ge=0, description="Inclusive. None means the last candle in the supplied data.")
    include_indicators: bool = Field(default=True, description="Whether to precompute+attach the strategy's indicator series for visualization.")
    include_smart_money: bool = Field(default=True, description="Whether to precompute+attach the strategy's detector series for visualization.")
    include_backtest_results: bool = Field(default=True, description="Whether to attach a supplied BacktestResult's trade-lifecycle markers for visualization.")


class ReplayTimeline(ReplayEngineModel):
    """The deterministic, ordered sequence of frame datetimes for one replay."""

    symbol: str
    timeframe: str
    total_frames: int = Field(ge=0)
    start_index: int = Field(ge=0, description="Index into the source data where frame 0 begins.")
    end_index: int = Field(ge=0, description="Inclusive index into the source data where the last frame ends.")
    start_datetime: str = ""
    end_datetime: str = ""
    frame_datetimes: tuple[str, ...] = Field(default_factory=tuple)


class TradeLifecycleMarker(ReplayEngineModel):
    """One trade-lifecycle marker (open/SL/TP/BE/partial-close/close) visible at a frame."""

    trade_id: str = Field(min_length=1)
    marker_type: str = Field(min_length=1, description='"OPEN" | "STOP_LOSS" | "TAKE_PROFIT" | "BREAK_EVEN" | "TRAILING_STOP" | "PARTIAL_CLOSE" | "SIGNAL" | "MANUAL" | "END_OF_DATA".')
    price: float | None = None


class IndicatorFrameValue(ReplayEngineModel):
    """One indicator output's value at a single frame."""

    local_name: str = Field(min_length=1)
    output_name: str = Field(min_length=1)
    value: float | None = None


class SmartMoneyFrameDetection(ReplayEngineModel):
    """One Smart Money detection anchored to a single frame."""

    local_name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    direction: str | None = None
    price: float | None = None
    top: float | None = None
    bottom: float | None = None


class ReplayFrame(ReplayEngineModel):
    """One immutable, point-in-time snapshot of the replay at a given index."""

    index: int = Field(ge=0)
    datetime: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    indicator_values: tuple[IndicatorFrameValue, ...] = Field(default_factory=tuple)
    smart_money_detections: tuple[SmartMoneyFrameDetection, ...] = Field(default_factory=tuple)
    trade_markers: tuple[TradeLifecycleMarker, ...] = Field(default_factory=tuple)


class ReplayEvent(ReplayEngineModel):
    """One entry in a replay session's event log."""

    event_type: ReplayEventType
    frame_index: int = Field(ge=0)
    datetime: str
    message: str = ""


class ReplayStatistics(ReplayEngineModel):
    """Aggregate, at-a-glance statistics for one replay preparation."""

    total_frames: int = Field(ge=0)
    symbol: str
    timeframe: str
    start_datetime: str
    end_datetime: str
    total_trade_markers: int = Field(ge=0, default=0)
    total_smart_money_detections: int = Field(ge=0, default=0)
    indicators_included: tuple[str, ...] = Field(default_factory=tuple)
    smart_money_included: tuple[str, ...] = Field(default_factory=tuple)


class ReplayResult(ReplayEngineModel):
    """The complete, immutable outcome of one replay preparation.

    Immutable, serializable, versioned, and hashable. Captures the
    deterministic setup of a replay (timeline + statistics) -- interactive
    playback itself happens afterwards through a `ReplayController` built
    from the same context, and is never re-invoked through this artifact.
    """

    result_id: str = Field(min_length=1)
    metadata: ReplayMetadata
    configuration: ReplayConfiguration
    timeline: ReplayTimeline
    statistics: ReplayStatistics
    events: tuple[ReplayEvent, ...] = Field(default_factory=tuple)
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
