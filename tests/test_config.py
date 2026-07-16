"""Tests for the configuration system."""

from app.config.paths import get_paths
from app.config.settings import Settings, get_settings


def test_settings_load_with_defaults() -> None:
    settings = get_settings()
    assert settings.app_name == "QuantForge AI"
    assert settings.environment in {"development", "staging", "production"}


def test_settings_is_cached_singleton() -> None:
    assert get_settings() is get_settings()


def test_settings_respects_env_prefix(monkeypatch) -> None:
    monkeypatch.setenv("QFAI_APP_NAME", "Custom Name")
    get_settings.cache_clear()
    try:
        assert Settings().app_name == "Custom Name"
    finally:
        get_settings.cache_clear()


def test_paths_are_resolved_and_created() -> None:
    paths = get_paths()
    assert paths.root.exists()
    assert paths.historical_data_dir.exists()
    assert paths.database_dir.exists()
