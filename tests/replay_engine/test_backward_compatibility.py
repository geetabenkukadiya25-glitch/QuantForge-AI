"""Confirms adding the Replay Engine didn't touch or break any prior phase."""

from app.config.paths import get_paths


def test_every_prior_engine_still_imports_cleanly() -> None:
    import app.backtesting_engine  # noqa: F401
    import app.context_engine  # noqa: F401
    import app.indicator_engine  # noqa: F401
    import app.optimization_engine  # noqa: F401
    import app.sdl  # noqa: F401
    import app.smart_money_engine  # noqa: F401
    import app.strategy_builder  # noqa: F401
    import app.validation_engine  # noqa: F401


def test_paths_still_exposes_every_prior_directory() -> None:
    paths = get_paths()
    for field in (
        "historical_data_dir", "sdl_dir", "context_engine_dir", "backtesting_engine_dir",
        "optimization_engine_dir", "validation_engine_dir", "replay_engine_dir", "replay_results_dir",
    ):
        assert getattr(paths, field) is not None


def test_replay_engine_dir_points_inside_the_app_tree() -> None:
    paths = get_paths()
    assert paths.replay_engine_dir == paths.app / "replay_engine"
    assert paths.replay_results_dir.exists()
