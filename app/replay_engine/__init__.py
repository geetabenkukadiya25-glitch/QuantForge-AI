"""Professional Replay Engine.

Replays historical candles exactly as they occurred. It MUST consume
Historical Data Engine outputs. It MAY consume Strategy Builder,
Indicator Engine, Smart Money Engine, and Backtesting Engine outputs
ONLY for visualization. It NEVER modifies strategy logic, NEVER
optimizes, NEVER executes trades, and NEVER connects to a broker or MT5.
"""

from app.replay_engine.compiler import ReplayCompiler
from app.replay_engine.context import ReplayContext
from app.replay_engine.controller import ReplayController
from app.replay_engine.cursor import ReplayCursor
from app.replay_engine.engine import ReplayEngine
from app.replay_engine.exceptions import (
    ReplayConfigurationError,
    ReplayDisabledError,
    ReplayEngineError,
    ReplayExecutionError,
    ReplayNavigationError,
    ReplayNotFoundError,
    ReplayRegistrationError,
    ReplayValidationError,
)
from app.replay_engine.frame import ReplayFrameSource, build_frame, build_frame_source
from app.replay_engine.metadata import REPLAY_RESULT_VERSION, ReplayMetadata
from app.replay_engine.models import (
    IndicatorFrameValue,
    PlaybackState,
    ReplayConfiguration,
    ReplayEvent,
    ReplayEventType,
    ReplayFrame,
    ReplayResult,
    ReplaySpeed,
    ReplayStatistics,
    ReplayTimeline,
    SmartMoneyFrameDetection,
    TradeLifecycleMarker,
)
from app.replay_engine.player import ReplayPlayer
from app.replay_engine.registry import ReplayRegistry
from app.replay_engine.report import ReplayReport
from app.replay_engine.runner import BaseReplayRunner, ReplayRunner, ReplaySession, SessionStatus
from app.replay_engine.serializer import ReplaySerializer
from app.replay_engine.timeline import build_timeline
from app.replay_engine.validator import ReplayCheckResult, ReplayIssue, ReplayValidator

__all__ = [
    "ReplayEngine",
    "ReplayRunner",
    "BaseReplayRunner",
    "ReplaySession",
    "SessionStatus",
    "ReplayContext",
    "ReplayCompiler",
    "ReplayValidator",
    "ReplayCheckResult",
    "ReplayIssue",
    "ReplaySerializer",
    "ReplayRegistry",
    "ReplayReport",
    "ReplayMetadata",
    "REPLAY_RESULT_VERSION",
    "ReplayConfiguration",
    "ReplayResult",
    "ReplayTimeline",
    "build_timeline",
    "ReplayCursor",
    "ReplayFrame",
    "ReplayFrameSource",
    "build_frame",
    "build_frame_source",
    "IndicatorFrameValue",
    "SmartMoneyFrameDetection",
    "TradeLifecycleMarker",
    "ReplayEvent",
    "ReplayEventType",
    "ReplayPlayer",
    "ReplayController",
    "PlaybackState",
    "ReplaySpeed",
    "ReplayStatistics",
    "ReplayEngineError",
    "ReplayConfigurationError",
    "ReplayValidationError",
    "ReplayExecutionError",
    "ReplayNavigationError",
    "ReplayNotFoundError",
    "ReplayDisabledError",
    "ReplayRegistrationError",
]
