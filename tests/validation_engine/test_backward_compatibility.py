"""Confirms the Validation Engine didn't touch or break any prior phase,
and that every later engine which consumes `ValidationResult` still gets
exactly the API it depends on."""

from app.config.paths import get_paths


def test_every_prior_engine_still_imports_cleanly() -> None:
    import app.backtesting_engine  # noqa: F401
    import app.context_engine  # noqa: F401
    import app.data_engine  # noqa: F401
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
        "optimization_engine_dir", "validation_engine_dir", "validation_results_dir",
        "indicator_engine_dir", "smart_money_engine_dir", "strategy_builder_dir",
        "chart_engine_dir", "data_engine_dir",
    ):
        assert getattr(paths, field) is not None


def test_validation_engine_dir_points_inside_the_app_tree() -> None:
    paths = get_paths()
    assert paths.validation_engine_dir == paths.app / "validation_engine"
    assert paths.validation_results_dir.exists()


def test_downstream_engines_still_depend_on_the_same_validation_result_api() -> None:
    """`portfolio_engine`, `ai_assistant`, and `ea_generator` all consume
    `ValidationResult` directly -- confirms this module still exposes
    exactly the shape those later phases depend on."""
    from app.validation_engine.metadata import VALIDATION_RESULT_VERSION, ValidationMetadata
    from app.validation_engine.models import ValidationResult

    assert VALIDATION_RESULT_VERSION == "1.0.0"
    assert hasattr(ValidationResult, "model_dump")
    assert "strategy_id" in ValidationMetadata.model_fields
    assert "result_version" in ValidationMetadata.model_fields


def test_shared_checksum_helper_still_exposes_expected_api() -> None:
    from app.core.checksums import canonical_json, compute_checksum, sha256_hex

    assert callable(canonical_json)
    assert callable(compute_checksum)
    assert callable(sha256_hex)
