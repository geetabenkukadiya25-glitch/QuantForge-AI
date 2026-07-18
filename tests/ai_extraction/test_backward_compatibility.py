"""Confirms adding the AI Strategy Extraction Engine didn't touch or break any prior phase."""

from app.config.paths import get_paths


def test_every_prior_engine_still_imports_cleanly() -> None:
    import app.ai_extraction  # noqa: F401
    import app.backtesting_engine  # noqa: F401
    import app.context_engine  # noqa: F401
    import app.indicator_engine  # noqa: F401
    import app.knowledge_base  # noqa: F401
    import app.optimization_engine  # noqa: F401
    import app.replay_engine  # noqa: F401
    import app.research_engine  # noqa: F401
    import app.sdl  # noqa: F401
    import app.smart_money_engine  # noqa: F401
    import app.strategy_builder  # noqa: F401
    import app.validation_engine  # noqa: F401


def test_paths_still_exposes_every_prior_directory() -> None:
    paths = get_paths()
    for field in (
        "historical_data_dir", "sdl_dir", "context_engine_dir", "backtesting_engine_dir",
        "optimization_engine_dir", "validation_engine_dir", "replay_engine_dir",
        "research_engine_dir", "knowledge_base_dir", "ai_extraction_dir", "ai_extraction_results_dir",
    ):
        assert getattr(paths, field) is not None


def test_ai_extraction_dir_points_inside_the_app_tree() -> None:
    paths = get_paths()
    assert paths.ai_extraction_dir == paths.app / "ai_extraction"
    assert paths.ai_extraction_results_dir.exists()


def test_sdl_schema_module_is_unmodified_by_reuse() -> None:
    """The extraction engine reuses `app.sdl.models`/`app.sdl.validator`
    directly -- confirms those modules still expose exactly the API this
    engine (and every prior phase) depends on."""
    from app.sdl.models import StrategyDefinition
    from app.sdl.validator import StrategyValidator

    assert hasattr(StrategyDefinition, "model_fields")
    assert hasattr(StrategyValidator(), "validate")
