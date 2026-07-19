"""Confirms adding Workspace Management (Phase 17.1) didn't touch or
break the completed Cloud Platform Foundation or any prior engine."""

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.registry import CloudRegistry
from app.config.paths import get_paths


def test_every_prior_engine_still_imports_cleanly() -> None:
    import app.ai_assistant  # noqa: F401
    import app.ai_extraction  # noqa: F401
    import app.backtesting_engine  # noqa: F401
    import app.context_engine  # noqa: F401
    import app.ea_generator  # noqa: F401
    import app.indicator_engine  # noqa: F401
    import app.knowledge_base  # noqa: F401
    import app.optimization_engine  # noqa: F401
    import app.portfolio_engine  # noqa: F401
    import app.replay_engine  # noqa: F401
    import app.research_engine  # noqa: F401
    import app.sdl  # noqa: F401
    import app.smart_money_engine  # noqa: F401
    import app.strategy_builder  # noqa: F401
    import app.validation_engine  # noqa: F401


def test_cloud_platform_foundation_still_works_standalone() -> None:
    """The Phase 17 foundation (`CloudCompiler`/`CloudRegistry`/`CloudPlatformContext`)
    must still work exactly as before, untouched by Phase 17.1."""
    context = CloudPlatformContext(workspace_id="ws1", label="Alpha")
    build = CloudCompiler().compile(context)
    registry = CloudRegistry()
    registry.register(build)
    assert registry.load(build.result_id) == build


def test_paths_still_exposes_every_prior_directory() -> None:
    paths = get_paths()
    for field in (
        "historical_data_dir",
        "sdl_dir",
        "context_engine_dir",
        "backtesting_engine_dir",
        "optimization_engine_dir",
        "validation_engine_dir",
        "replay_engine_dir",
        "research_engine_dir",
        "knowledge_base_dir",
        "ai_extraction_dir",
        "portfolio_engine_dir",
        "ai_assistant_dir",
        "ea_generator_dir",
    ):
        assert getattr(paths, field) is not None


def test_workspace_management_adds_no_new_path_fields() -> None:
    """This phase is in-memory only -- it must not require any new results
    directory on disk (no filesystem access is part of its offline scope)."""
    paths = get_paths()
    assert not hasattr(paths, "cloud_platform_dir")
    assert not hasattr(paths, "workspace_dir")


def test_workspace_modules_import_cleanly_alongside_the_foundation() -> None:
    import app.cloud_platform  # noqa: F401
    import app.cloud_platform.workspace  # noqa: F401
    import app.cloud_platform.workspace_manager  # noqa: F401
    import app.cloud_platform.workspace_registry  # noqa: F401
    import app.cloud_platform.workspace_report  # noqa: F401
    import app.cloud_platform.workspace_statistics  # noqa: F401
