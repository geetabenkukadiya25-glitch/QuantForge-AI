"""`app.cloud_platform.registry`: in-memory registration, enable/disable, search."""

import pytest

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.exceptions import CloudDisabledError, CloudNotFoundError, CloudRegistrationError
from app.cloud_platform.registry import CloudRegistry


@pytest.fixture
def build(cloud_platform_context: CloudPlatformContext):
    return CloudCompiler().compile(cloud_platform_context)


def test_register_then_load(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    assert registry.load(build.result_id) == build


def test_register_duplicate_without_overwrite_raises(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    with pytest.raises(CloudRegistrationError):
        registry.register(build)


def test_register_duplicate_with_overwrite_succeeds(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    registry.register(build, overwrite=True)
    assert registry.load(build.result_id) == build


def test_load_unknown_id_raises(build) -> None:
    registry = CloudRegistry()
    with pytest.raises(CloudNotFoundError):
        registry.load("unknown-id")


def test_registered_build_is_enabled_by_default(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    assert registry.is_enabled(build.result_id)
    assert registry.require_enabled(build.result_id) == build


def test_disable_then_require_enabled_raises(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    registry.disable(build.result_id)
    assert not registry.is_enabled(build.result_id)
    with pytest.raises(CloudDisabledError):
        registry.require_enabled(build.result_id)


def test_disable_then_enable_restores_availability(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    registry.disable(build.result_id)
    registry.enable(build.result_id)
    assert registry.is_enabled(build.result_id)


def test_list_returns_sorted_metadata(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    metadata_list = registry.list()
    assert len(metadata_list) == 1
    assert metadata_list[0].workspace_id == build.metadata.workspace_id


def test_search_by_workspace_id(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    results = registry.search(workspace_id=build.metadata.workspace_id)
    assert len(results) == 1
    assert registry.search(workspace_id="does-not-exist") == []


def test_list_excludes_disabled_when_requested(build) -> None:
    registry = CloudRegistry()
    registry.register(build)
    registry.disable(build.result_id)
    assert registry.list(include_disabled=False) == []
    assert len(registry.list(include_disabled=True)) == 1
