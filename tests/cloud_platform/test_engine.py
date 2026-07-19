"""`app.cloud_platform.engine`: the top-level `CloudPlatformEngine` facade."""

import pytest

from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.engine import CloudPlatformEngine
from app.cloud_platform.exceptions import CloudValidationError
from app.core.base_engine import BaseEngine


def test_engine_is_a_base_engine() -> None:
    assert isinstance(CloudPlatformEngine(), BaseEngine)
    assert CloudPlatformEngine.name == "CloudPlatformEngine"


def test_execute_returns_a_build(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudPlatformEngine().execute(cloud_platform_context)
    assert build.workspace.workspace_id == "workspace-1"


def test_run_aliases_execute(cloud_platform_context: CloudPlatformContext) -> None:
    engine = CloudPlatformEngine()
    assert engine.run(cloud_platform_context).checksum == engine.execute(cloud_platform_context).checksum


def test_execute_raises_on_invalid_context() -> None:
    with pytest.raises(CloudValidationError):
        CloudPlatformEngine().execute(CloudPlatformContext(workspace_id=""))


def test_try_execute_never_raises() -> None:
    session = CloudPlatformEngine().try_execute(CloudPlatformContext(workspace_id=""))
    assert not session.is_successful
