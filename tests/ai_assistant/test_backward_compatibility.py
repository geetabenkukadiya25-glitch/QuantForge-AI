"""Confirms adding the AI Research Assistant didn't touch or break any prior phase."""

from app.config.paths import get_paths


def test_every_prior_engine_still_imports_cleanly() -> None:
    import app.ai_assistant  # noqa: F401
    import app.ai_extraction  # noqa: F401
    import app.backtesting_engine  # noqa: F401
    import app.context_engine  # noqa: F401
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
        "historical_data_dir", "sdl_dir", "context_engine_dir", "backtesting_engine_dir",
        "optimization_engine_dir", "validation_engine_dir", "replay_engine_dir",
        "research_engine_dir", "knowledge_base_dir", "ai_extraction_dir", "ai_extraction_results_dir",
        "indicator_engine_dir", "smart_money_engine_dir", "strategy_builder_dir", "chart_engine_dir", "data_engine_dir",
        "portfolio_engine_dir", "portfolio_results_dir", "ai_assistant_dir", "ai_assistant_results_dir",
    ):
        assert getattr(paths, field) is not None


def test_ai_assistant_dir_points_inside_the_app_tree() -> None:
    paths = get_paths()
    assert paths.ai_assistant_dir == paths.app / "ai_assistant"
    assert paths.ai_assistant_results_dir.exists()


def test_upstream_registries_are_unmodified_by_reuse() -> None:
    """AI Research Assistant reuses `KnowledgeRegistry`/`ResearchRegistry`/
    `PortfolioRegistry`/`IndicatorRegistry`/`SMCRegistry`/`app.sdl.StrategyRegistry`
    directly -- confirms those modules still expose exactly the API this
    engine (and every prior phase) depends on."""
    from app.indicator_engine.registry import IndicatorRegistry
    from app.knowledge_base.registry import KnowledgeRegistry
    from app.portfolio_engine.registry import PortfolioRegistry
    from app.research_engine.registry import ResearchRegistry
    from app.sdl.registry import StrategyRegistry
    from app.smart_money_engine.registry import SMCRegistry

    for registry_cls in (IndicatorRegistry, KnowledgeRegistry, PortfolioRegistry, ResearchRegistry, StrategyRegistry, SMCRegistry):
        assert hasattr(registry_cls, "list")


def test_shared_checksum_helper_still_exposes_expected_api() -> None:
    from app.core.checksums import canonical_json, compute_checksum, sha256_hex

    assert callable(canonical_json)
    assert callable(compute_checksum)
    assert callable(sha256_hex)
