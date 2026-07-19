"""`app.cloud_platform.runner`: validate-then-compile orchestration."""

import pytest

from app.cloud_platform.context import CloudPlatformContext, ProjectDraft
from app.cloud_platform.exceptions import CloudValidationError
from app.cloud_platform.models import DatasetReference
from app.cloud_platform.runner import CloudPlatformRunner, SessionStatus


def test_execute_returns_a_compiled_build(cloud_platform_context: CloudPlatformContext) -> None:
    build = CloudPlatformRunner().execute(cloud_platform_context)
    assert build.workspace.workspace_id == "workspace-1"


def test_execute_raises_on_invalid_context() -> None:
    invalid_context = CloudPlatformContext(workspace_id="")
    with pytest.raises(CloudValidationError):
        CloudPlatformRunner().execute(invalid_context)


def test_try_execute_never_raises_and_reports_failure() -> None:
    invalid_context = CloudPlatformContext(workspace_id="")
    session = CloudPlatformRunner().try_execute(invalid_context)
    assert session.status == SessionStatus.FAILED
    assert not session.is_successful
    assert session.result is None
    assert not session.validation.is_valid


def test_try_execute_reports_success(cloud_platform_context: CloudPlatformContext) -> None:
    session = CloudPlatformRunner().try_execute(cloud_platform_context)
    assert session.status == SessionStatus.COMPLETED
    assert session.is_successful
    assert session.result is not None
    assert session.validation.is_valid


def test_run_aliases_execute(cloud_platform_context: CloudPlatformContext) -> None:
    runner = CloudPlatformRunner()
    assert runner.run(cloud_platform_context).workspace.workspace_id == "workspace-1"
