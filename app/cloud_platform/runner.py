"""Orchestrates one workspace compilation: validate, compile.

`CloudPlatformRunner` is the engine-facing orchestrator (implements
`BaseEngine`); `CloudSession` is the outcome record of one run attempt,
mirroring `app.replay_engine.runner.ReplayRunner`'s "never raises,
inspect `.is_successful`" shape via `try_execute`, plus a raising
`execute()` for callers that prefer exceptions.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.exceptions import CloudValidationError
from app.cloud_platform.models import CloudBuild
from app.cloud_platform.validator import CloudCheckResult, CloudValidator
from app.core.base_engine import BaseEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SessionStatus(str, Enum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class CloudSession:
    """The outcome record of one `CloudPlatformRunner.try_execute()` call."""

    session_id: str
    context: CloudPlatformContext
    status: SessionStatus = SessionStatus.RUNNING
    validation: CloudCheckResult | None = None
    result: CloudBuild | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def is_successful(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.result is not None


class BaseCloudRunner(BaseEngine, ABC):
    """Common contract every workspace-compiling engine implements."""

    name = "BaseCloudRunner"

    @abstractmethod
    def execute(self, context: CloudPlatformContext) -> CloudBuild:
        """Compile a workspace context and return its `CloudBuild`.

        Raises:
            CloudValidationError: if `context` fails pre-compile validation.
        """

    def run(self, *args: Any, **kwargs: Any) -> CloudBuild:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)


class CloudPlatformRunner(BaseCloudRunner):
    """The default `BaseCloudRunner` implementation: validate, then compile."""

    name = "CloudPlatformRunner"

    def __init__(self, validator: CloudValidator | None = None, compiler: CloudCompiler | None = None) -> None:
        self._validator = validator or CloudValidator()
        self._compiler = compiler or CloudCompiler()

    def execute(self, context: CloudPlatformContext) -> CloudBuild:
        """Compile a workspace context, raising on validation failure.

        Raises:
            CloudValidationError: if `context` fails pre-compile validation.
        """
        session = self.try_execute(context)
        if not session.is_successful:
            assert session.validation is not None  # guaranteed by is_successful
            raise CloudValidationError(session.validation.errors)
        assert session.result is not None  # guaranteed by is_successful
        return session.result

    def try_execute(self, context: CloudPlatformContext) -> CloudSession:
        """Validate then compile `context`. Never raises."""
        session = CloudSession(session_id=str(uuid.uuid4()), context=context)

        validation = self._validator.validate(context)
        session.validation = validation
        if not validation.is_valid:
            session.status = SessionStatus.FAILED
            session.completed_at = datetime.now(timezone.utc)
            logger.warning("Cloud session %s failed validation.", session.session_id)
            return session

        result = self._compiler.compile(context)

        session.result = result
        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        logger.info("Cloud session %s completed (workspace=%s).", session.session_id, context.workspace_id)
        return session
