"""
Centralized filesystem paths.

Every module that needs to read or write project files should resolve the
location through `get_paths()` rather than constructing paths by hand, so
the on-disk layout stays a single source of truth.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.config.settings import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    """Resolved, absolute paths for every project data directory."""

    root: Path
    app: Path

    data_dir: Path
    historical_data_dir: Path
    downloads_dir: Path
    data_engine_dir: Path

    strategies_dir: Path
    generated_strategies_dir: Path
    strategy_builder_dir: Path

    sdl_dir: Path
    sdl_library_dir: Path

    indicator_engine_dir: Path
    smart_money_engine_dir: Path
    chart_engine_dir: Path

    context_engine_dir: Path
    context_snapshots_dir: Path

    backtesting_engine_dir: Path
    backtest_results_dir: Path

    optimization_engine_dir: Path
    optimization_results_dir: Path

    validation_engine_dir: Path
    validation_results_dir: Path

    replay_engine_dir: Path
    replay_results_dir: Path

    research_engine_dir: Path
    research_results_dir: Path

    knowledge_base_dir: Path
    knowledge_base_entries_dir: Path

    ai_extraction_dir: Path
    ai_extraction_results_dir: Path

    portfolio_engine_dir: Path
    portfolio_results_dir: Path

    ai_assistant_dir: Path
    ai_assistant_results_dir: Path

    ea_generator_dir: Path
    ea_generator_results_dir: Path

    analytics_dir: Path
    reports_dir: Path
    charts_dir: Path

    database_dir: Path
    database_file: Path

    logs_dir: Path


@lru_cache
def get_paths() -> Paths:
    """Return a cached singleton `Paths` instance, creating directories as needed."""
    settings = get_settings()
    app_dir = PROJECT_ROOT / "app"

    paths = Paths(
        root=PROJECT_ROOT,
        app=app_dir,
        data_dir=app_dir / "data",
        historical_data_dir=app_dir / "data" / "historical",
        downloads_dir=app_dir / "data" / "downloads",
        data_engine_dir=app_dir / "data_engine",
        strategies_dir=app_dir / "strategies",
        generated_strategies_dir=app_dir / "strategies" / "generated",
        strategy_builder_dir=app_dir / "strategy_builder",
        sdl_dir=app_dir / "sdl",
        sdl_library_dir=app_dir / "sdl" / "library",
        indicator_engine_dir=app_dir / "indicator_engine",
        smart_money_engine_dir=app_dir / "smart_money_engine",
        chart_engine_dir=app_dir / "chart_engine",
        context_engine_dir=app_dir / "context_engine",
        context_snapshots_dir=app_dir / "context_engine" / "snapshots",
        backtesting_engine_dir=app_dir / "backtesting_engine",
        backtest_results_dir=app_dir / "backtesting_engine" / "results",
        optimization_engine_dir=app_dir / "optimization_engine",
        optimization_results_dir=app_dir / "optimization_engine" / "results",
        validation_engine_dir=app_dir / "validation_engine",
        validation_results_dir=app_dir / "validation_engine" / "results",
        replay_engine_dir=app_dir / "replay_engine",
        replay_results_dir=app_dir / "replay_engine" / "results",
        research_engine_dir=app_dir / "research_engine",
        research_results_dir=app_dir / "research_engine" / "results",
        knowledge_base_dir=app_dir / "knowledge_base",
        knowledge_base_entries_dir=app_dir / "knowledge_base" / "entries",
        ai_extraction_dir=app_dir / "ai_extraction",
        ai_extraction_results_dir=app_dir / "ai_extraction" / "results",
        portfolio_engine_dir=app_dir / "portfolio_engine",
        portfolio_results_dir=app_dir / "portfolio_engine" / "results",
        ai_assistant_dir=app_dir / "ai_assistant",
        ai_assistant_results_dir=app_dir / "ai_assistant" / "results",
        ea_generator_dir=app_dir / "ea_generator",
        ea_generator_results_dir=app_dir / "ea_generator" / "results",
        analytics_dir=app_dir / "analytics",
        reports_dir=app_dir / "analytics" / "reports",
        charts_dir=app_dir / "analytics" / "charts",
        database_dir=app_dir / "database",
        database_file=app_dir / "database" / settings.database_name,
        logs_dir=PROJECT_ROOT / "logs",
    )

    for directory in (
        paths.historical_data_dir,
        paths.downloads_dir,
        paths.generated_strategies_dir,
        paths.sdl_library_dir,
        paths.context_snapshots_dir,
        paths.backtest_results_dir,
        paths.optimization_results_dir,
        paths.validation_results_dir,
        paths.replay_results_dir,
        paths.research_results_dir,
        paths.knowledge_base_entries_dir,
        paths.ai_extraction_results_dir,
        paths.portfolio_results_dir,
        paths.ai_assistant_results_dir,
        paths.ea_generator_results_dir,
        paths.reports_dir,
        paths.charts_dir,
        paths.database_dir,
        paths.logs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    return paths
