"""Confirms adding the Cloud Platform Foundation didn't touch or break any prior phase."""

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
        "replay_results_dir",
        "research_engine_dir",
        "knowledge_base_dir",
        "ai_extraction_dir",
        "portfolio_engine_dir",
        "ai_assistant_dir",
        "ea_generator_dir",
    ):
        assert getattr(paths, field) is not None


def test_cloud_platform_adds_no_new_path_fields() -> None:
    """This phase is in-memory only -- it must not require any new results
    directory on disk (no filesystem access is part of its offline scope)."""
    paths = get_paths()
    assert not hasattr(paths, "cloud_platform_dir")
    assert not hasattr(paths, "cloud_platform_results_dir")


def test_cloud_platform_module_imports_cleanly_alongside_every_prior_engine() -> None:
    import app.cloud_platform  # noqa: F401
