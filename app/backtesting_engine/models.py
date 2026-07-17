"""The immutable backtest artifact and its building blocks.

Every model here is `frozen=True` -- hashable and immutable by
construction, the same trade-off `app.strategy_builder`, `app.sdl`, and
`app.context_engine` make for their own artifacts. `BacktestResult` is the
single artifact this engine produces: a deterministic, versioned,
serializable record of one historical replay. It contains no broker
handles, no live connections, and no mutable simulation state -- that
lives only transiently inside `TradeSimulator`/`PositionManager` while a
run is in progress.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.backtesting_engine.metadata import BacktestMetadata


class BacktestEngineModel(BaseModel):
    """Base class for every backtesting_engine model: forbids unknown fields, is immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class TradeDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    BREAK_EVEN = "BREAK_EVEN"
    TRAILING_STOP = "TRAILING_STOP"
    PARTIAL_CLOSE = "PARTIAL_CLOSE"
    SIGNAL = "SIGNAL"
    MANUAL = "MANUAL"
    END_OF_DATA = "END_OF_DATA"


class BacktestConfiguration(BacktestEngineModel):
    """Configurable execution assumptions for one backtest run.

    Every field here is a *placeholder-level* assumption (per the Phase 9
    spec: "Include placeholders for Spread, Slippage, Commission, Swap,
    Latency") -- simple, deterministic, and documented, not a broker-grade
    execution model. No field here ever contacts a broker or MT5.
    """

    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    initial_balance: float = Field(gt=0, default=10_000.0)
    lot_size: float = Field(gt=0, default=1.0)
    point_value: float = Field(gt=0, default=1.0, description="Account-currency value of one price point per lot.")
    spread_points: float = Field(ge=0, default=0.0, description="Fixed spread applied to every fill, in points.")
    slippage_points: float = Field(ge=0, default=0.0, description="Fixed adverse slippage applied to every fill, in points.")
    commission_per_lot: float = Field(ge=0, default=0.0, description="Flat commission charged per lot, per round turn.")
    swap_long_per_day: float = Field(default=0.0, description="Swap charged/credited per lot, per day, for long positions.")
    swap_short_per_day: float = Field(default=0.0, description="Swap charged/credited per lot, per day, for short positions.")
    latency_bars: int = Field(ge=0, default=0, description="Signal-to-fill delay, in bars (framework placeholder; 0 = same-bar fill).")
    max_open_positions: int = Field(ge=1, default=1)
    stop_loss_points: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Configuration-level stop-loss distance in price points, applied to every "
            "entry. StrategyModel (Phase 8) does not yet carry SDL's per-strategy "
            "RiskManagement block, so risk levels are a run-level assumption for now "
            "-- see PROJECT_IDEAS.md."
        ),
    )
    take_profit_points: float | None = Field(default=None, ge=0, description="Configuration-level take-profit distance in price points.")
    risk_free_rate: float = Field(default=0.0, description="Annualized risk-free rate used by the Sharpe/Sortino framework calculations.")
    enable_trailing_stop: bool = Field(default=False, description="Framework flag only -- trailing distance is not yet configurable.")
    enable_partial_close: bool = Field(default=False, description="Framework flag only -- partial-close ratio is not yet configurable.")


class Trade(BacktestEngineModel):
    """One completed (or still-open) simulated position."""

    trade_id: str = Field(min_length=1)
    direction: TradeDirection
    entry_index: int = Field(ge=0)
    entry_datetime: str
    entry_price: float
    volume: float = Field(gt=0)
    stop_loss: float | None = None
    take_profit: float | None = None
    exit_index: int | None = None
    exit_datetime: str | None = None
    exit_price: float | None = None
    status: TradeStatus = TradeStatus.OPEN
    exit_reason: ExitReason | None = None
    gross_profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0

    @property
    def net_profit(self) -> float:
        return self.gross_profit - self.commission - self.swap


class EquityPoint(BacktestEngineModel):
    index: int = Field(ge=0)
    datetime: str
    equity: float


class EquityCurve(BacktestEngineModel):
    """Balance plus floating (unrealized) profit, sampled once per candle."""

    points: tuple[EquityPoint, ...] = Field(default_factory=tuple)

    @property
    def final_equity(self) -> float | None:
        return self.points[-1].equity if self.points else None


class BalancePoint(BacktestEngineModel):
    index: int = Field(ge=0)
    datetime: str
    balance: float


class BalanceCurve(BacktestEngineModel):
    """Realized balance only, sampled at every trade close."""

    points: tuple[BalancePoint, ...] = Field(default_factory=tuple)

    @property
    def final_balance(self) -> float | None:
        return self.points[-1].balance if self.points else None


class DrawdownPoint(BacktestEngineModel):
    index: int = Field(ge=0)
    datetime: str
    drawdown: float
    drawdown_pct: float


class DrawdownReport(BacktestEngineModel):
    """Peak-to-trough decline of the equity curve over the full run."""

    points: tuple[DrawdownPoint, ...] = Field(default_factory=tuple)
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    average_drawdown: float = 0.0


class PerformanceStatistics(BacktestEngineModel):
    """Aggregate trade and equity-curve statistics for one run."""

    total_trades: int = Field(ge=0, default=0)
    winning_trades: int = Field(ge=0, default=0)
    losing_trades: int = Field(ge=0, default=0)
    win_rate: float = 0.0
    profit_factor: float | None = None
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    expectancy: float = 0.0
    max_drawdown: float = 0.0
    average_drawdown: float = 0.0
    recovery_factor: float | None = None
    sharpe_ratio: float | None = Field(default=None, description="Framework-level, simplified (non-annualized-return) calculation.")
    sortino_ratio: float | None = Field(default=None, description="Framework-level, simplified calculation.")
    calmar_ratio: float | None = Field(default=None, description="Framework-level, simplified calculation.")


class ExecutionEvent(BacktestEngineModel):
    """One entry in the human-readable execution timeline report."""

    index: int = Field(ge=0)
    datetime: str
    event_type: str
    message: str


class BacktestResult(BacktestEngineModel):
    """The complete, immutable outcome of one historical strategy replay.

    Immutable, serializable, versioned, and hashable -- the single
    artifact downstream engines (Optimization Engine, Walk Forward &
    Monte Carlo, Replay Engine) will consume instead of re-running the
    simulation themselves.
    """

    result_id: str = Field(min_length=1)
    metadata: BacktestMetadata
    configuration: BacktestConfiguration
    trades: tuple[Trade, ...] = Field(default_factory=tuple)
    equity_curve: EquityCurve
    balance_curve: BalanceCurve
    drawdown_report: DrawdownReport
    statistics: PerformanceStatistics
    execution_timeline: tuple[ExecutionEvent, ...] = Field(default_factory=tuple)
    checksum: str = Field(min_length=1)
    built_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
