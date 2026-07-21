"""Backtesting Engine.

Simulates historical strategy execution ONLY -- deterministic,
candle-by-candle replay of a compiled `app.strategy_builder.StrategyModel`
against historical OHLCV data. It NEVER connects to a broker, NEVER
places a live order, and NEVER requires MetaTrader.

Consumes ONLY the Historical Data Engine, Strategy Builder, Market
Context Engine, Indicator Engine, and Smart Money Engine -- never a
broker API, never MT5.
"""

from app.backtesting_engine.compiler import BacktestCompiler
from app.backtesting_engine.context import BacktestContext
from app.backtesting_engine.engine import BacktestingEngine
from app.backtesting_engine.exceptions import (
    BacktestConfigurationError,
    BacktestDataError,
    BacktestDisabledError,
    BacktestExecutionError,
    BacktestingEngineError,
    BacktestNotFoundError,
    BacktestRegistrationError,
    BacktestValidationError,
)
from app.backtesting_engine.expression import evaluate_condition
from app.backtesting_engine.journal import TradeJournal
from app.backtesting_engine.metadata import BACKTEST_RESULT_VERSION, BacktestMetadata
from app.backtesting_engine.models import (
    BacktestConfiguration,
    BacktestResult,
    BalanceCurve,
    BalancePoint,
    DrawdownPoint,
    DrawdownReport,
    EquityCurve,
    EquityPoint,
    ExecutionEvent,
    ExitReason,
    PerformanceStatistics,
    Trade,
    TradeDirection,
    TradeStatus,
)
from app.backtesting_engine.order import ExecutionEngine, OrderSimulator, PendingOrder
from app.backtesting_engine.position import PositionManager
from app.backtesting_engine.registry import BacktestRegistry
from app.backtesting_engine.runner import BacktestRunner, BacktestSession, BaseBacktestRunner, SessionStatus
from app.backtesting_engine.serializer import BacktestSerializer
from app.backtesting_engine.simulator import ProgressCallback, SimulationOutput, TradeSimulator
from app.backtesting_engine.statistics import DrawdownAnalyzer, PerformanceAnalyzer, StatisticsEngine
from app.backtesting_engine.validator import BacktestValidator, ValidationIssue, ValidationResult

__all__ = [
    "BacktestingEngine",
    "BacktestRunner",
    "BaseBacktestRunner",
    "BacktestSession",
    "SessionStatus",
    "BacktestContext",
    "BacktestCompiler",
    "BacktestValidator",
    "ValidationResult",
    "ValidationIssue",
    "BacktestSerializer",
    "BacktestRegistry",
    "BacktestMetadata",
    "BACKTEST_RESULT_VERSION",
    "BacktestConfiguration",
    "BacktestResult",
    "Trade",
    "TradeDirection",
    "TradeStatus",
    "ExitReason",
    "EquityCurve",
    "EquityPoint",
    "BalanceCurve",
    "BalancePoint",
    "DrawdownReport",
    "DrawdownPoint",
    "PerformanceStatistics",
    "ExecutionEvent",
    "TradeSimulator",
    "SimulationOutput",
    "ProgressCallback",
    "PositionManager",
    "OrderSimulator",
    "PendingOrder",
    "ExecutionEngine",
    "DrawdownAnalyzer",
    "PerformanceAnalyzer",
    "StatisticsEngine",
    "TradeJournal",
    "evaluate_condition",
    "BacktestingEngineError",
    "BacktestConfigurationError",
    "BacktestDataError",
    "BacktestValidationError",
    "BacktestExecutionError",
    "BacktestNotFoundError",
    "BacktestDisabledError",
    "BacktestRegistrationError",
]
