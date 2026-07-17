"""Orchestrates one replay preparation: validate, build timeline, precompute, compile.

`ReplayRunner` is the engine-facing orchestrator (implements `BaseEngine`);
`ReplaySession` is the outcome record of one run attempt, mirroring
`app.validation_engine.runner.ValidationRunner`'s "never raises, inspect
`.is_successful`" shape via `try_execute`, plus a raising `execute()` for
callers that prefer exceptions.

The `ReplayResult` this produces captures the deterministic setup of a
replay (timeline + statistics) -- the actual interactive playback (play/
pause/step/jump) happens afterwards through a `ReplayController` built via
`build_controller()`, driven directly by the caller (e.g. the Streamlit
dashboard), and never re-enters this runner. Neither this runner nor the
controller it builds ever optimizes, ever backtests independently, ever
modifies strategy logic, or ever connects to a broker or MT5.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.core.base_engine import BaseEngine
from app.replay_engine.compiler import ReplayCompiler
from app.replay_engine.context import ReplayContext
from app.replay_engine.controller import ReplayController
from app.replay_engine.exceptions import ReplayValidationError
from app.replay_engine.frame import build_frame_source
from app.replay_engine.models import ReplayResult, ReplayStatistics, ReplayTimeline
from app.replay_engine.timeline import build_timeline
from app.replay_engine.validator import ReplayCheckResult, ReplayValidator
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class ReplaySession:
    """The outcome record of one `ReplayRunner.try_execute()` call."""

    session_id: str
    context: ReplayContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: ReplayCheckResult | None = None
    result: ReplayResult | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseReplayRunner(BaseEngine, ABC):
    """Common contract every replay-preparing engine implements."""

    name = "BaseReplayRunner"

    @abstractmethod
    def execute(self, context: ReplayContext) -> ReplayResult:
        """Prepare a replay and return its `ReplayResult`.

        Raises:
            ReplayValidationError: if `context` fails pre-execution validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> ReplayResult:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class ReplayRunner(BaseReplayRunner):
    """The default `BaseReplayRunner` implementation: validate, build timeline, precompute, compile."""

    name = "ReplayRunner"

    def __init__(self, validator: ReplayValidator | None = None, compiler: ReplayCompiler | None = None) -> None:
        self._validator = validator or ReplayValidator()
        self._compiler = compiler or ReplayCompiler()

    def execute(self, context: ReplayContext) -> ReplayResult:
        """Prepare a replay, raising on validation failure.

        Raises:
            ReplayValidationError: if `context` fails pre-execution validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise ReplayValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: ReplayContext) -> ReplaySession:
        """Validate, build the timeline, precompute, and compile `context`. Never raises."""
        session = ReplaySession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Replay session %s failed validation.", session.session_id)
            return session

        timeline = build_timeline(context)
        frame_source = build_frame_source(context)
        statistics = self._statistics(context, timeline, frame_source)
        result = self._compiler.compile(context, timeline, statistics)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Replay session %s completed (%d frame(s)).", session.session_id, timeline.total_frames)
        return session

    def build_controller(self, context: ReplayContext) -> ReplayController:
        """Prepare an interactive `ReplayController` for `context`.

        Raises:
            ReplayValidationError: if `context` fails pre-execution validation.
        """
        validation = self._validator.validate(context)
        if not validation.is_valid:
            raise ReplayValidationError(validation.errors)
        timeline = build_timeline(context)
        return ReplayController(context=context, timeline=timeline)

    @staticmethod
    def _statistics(context: ReplayContext, timeline: ReplayTimeline, frame_source) -> ReplayStatistics:
        config = context.configuration
        indicators_included = tuple(ref.local_name for ref in context.strategy_model.indicators) if context.strategy_model and config.include_indicators else ()
        smart_money_included = tuple(ref.local_name for ref in context.strategy_model.detectors) if context.strategy_model and config.include_smart_money else ()
        total_detections = sum(len(v) for v in frame_source.detections_by_index.values())
        total_markers = sum(len(v) for v in frame_source.markers_by_index.values())
        return ReplayStatistics(
            total_frames=timeline.total_frames,
            symbol=timeline.symbol,
            timeframe=timeline.timeframe,
            start_datetime=timeline.start_datetime,
            end_datetime=timeline.end_datetime,
            total_trade_markers=total_markers,
            total_smart_money_detections=total_detections,
            indicators_included=indicators_included,
            smart_money_included=smart_money_included,
        )
