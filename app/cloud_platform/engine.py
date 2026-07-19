"""Top-level facade for the Cloud Platform Foundation.

`CloudPlatformEngine` composes `CloudValidator`, `CloudCompiler`, and
`CloudPlatformRunner` into the single entrypoint most callers need. This
is a management layer only: it stores references (ids, names,
checksums) to artifacts produced by other engines, and never inspects
their internals. It implements no authentication, no networking, no
synchronization, no API, no background workers, and no database --
everything in this phase is in-memory and offline. Implements
`BaseEngine` (`run` aliases `execute`).
"""

from typing import Any

from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.models import CloudBuild
from app.cloud_platform.runner import CloudPlatformRunner, CloudSession
from app.core.base_engine import BaseEngine
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CloudPlatformEngine(BaseEngine):
    """Compiles a workspace's project/reference metadata into a deterministic `CloudBuild`.

    Consumes only caller-supplied ids, names, and checksums describing
    other engines' outputs -- it never reads, imports, or depends on
    Backtesting, Optimization, Replay, Validation, Research, Portfolio,
    or EA Generator internals.
    """

    name = "CloudPlatformEngine"

    def __init__(self, runner: CloudPlatformRunner | None = None) -> None:
        self._runner = runner or CloudPlatformRunner()

    def run(self, *args: Any, **kwargs: Any) -> CloudBuild:
        """`BaseEngine` entrypoint; delegates to `execute`."""
        return self.execute(*args, **kwargs)

    def execute(self, context: CloudPlatformContext) -> CloudBuild:
        """Compile one workspace context, raising on validation failure.

        Raises:
            CloudValidationError: if `context` fails pre-compile validation.
        """
        return self._runner.execute(context)

    def try_execute(self, context: CloudPlatformContext) -> CloudSession:
        """Compile one workspace context. Never raises -- inspect the returned session."""
        return self._runner.try_execute(context)
