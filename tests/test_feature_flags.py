"""Tests for app.core.feature_flags."""

import pytest

from app.core.feature_flags import (
    ENV_PREFIX,
    FeatureFlag,
    FeatureFlagError,
    FeatureFlagManager,
    FeatureStage,
)


def test_experimental_flag_cannot_default_enabled() -> None:
    with pytest.raises(FeatureFlagError):
        FeatureFlag(name="x", stage=FeatureStage.EXPERIMENTAL, enabled_by_default=True)


def test_stable_flag_default_enabled_true() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="stable_on", stage=FeatureStage.STABLE, enabled_by_default=True))
    assert manager.is_enabled("stable_on") is True


def test_experimental_flag_default_disabled() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="exp", stage=FeatureStage.EXPERIMENTAL))
    assert manager.is_enabled("exp") is False


def test_unknown_flag_raises() -> None:
    manager = FeatureFlagManager()
    with pytest.raises(FeatureFlagError):
        manager.is_enabled("does-not-exist")


def test_register_duplicate_identical_flag_is_idempotent() -> None:
    manager = FeatureFlagManager()
    flag = FeatureFlag(name="dup", stage=FeatureStage.STABLE)
    manager.register(flag)
    manager.register(flag)  # should not raise


def test_register_conflicting_duplicate_raises() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="dup", stage=FeatureStage.STABLE, enabled_by_default=True))
    with pytest.raises(FeatureFlagError):
        manager.register(FeatureFlag(name="dup", stage=FeatureStage.STABLE, enabled_by_default=False))


def test_enable_and_disable_override_default() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="f", stage=FeatureStage.STABLE, enabled_by_default=False))
    manager.enable("f")
    assert manager.is_enabled("f") is True
    manager.disable("f")
    assert manager.is_enabled("f") is False


def test_clear_override_reverts_to_default() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="f", stage=FeatureStage.STABLE, enabled_by_default=True))
    manager.disable("f")
    assert manager.is_enabled("f") is False
    manager.clear_override("f")
    assert manager.is_enabled("f") is True


def test_experimental_locked_off_in_production(monkeypatch) -> None:
    from app.config.settings import get_settings

    monkeypatch.setenv("QFAI_ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        manager = FeatureFlagManager()
        manager.register(FeatureFlag(name="exp", stage=FeatureStage.EXPERIMENTAL))
        manager.enable("exp")  # attempt to force it on
        assert manager.is_enabled("exp") is False
        assert manager.status("exp").source == "production_lock"
    finally:
        get_settings.cache_clear()


def test_stable_flag_still_works_in_production(monkeypatch) -> None:
    from app.config.settings import get_settings

    monkeypatch.setenv("QFAI_ENVIRONMENT", "production")
    get_settings.cache_clear()
    try:
        manager = FeatureFlagManager()
        manager.register(FeatureFlag(name="stable", stage=FeatureStage.STABLE, enabled_by_default=True))
        assert manager.is_enabled("stable") is True
    finally:
        get_settings.cache_clear()


def test_env_override(monkeypatch) -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="env_flag", stage=FeatureStage.STABLE, enabled_by_default=False))
    monkeypatch.setenv(f"{ENV_PREFIX}ENV_FLAG", "true")
    assert manager.is_enabled("env_flag") is True
    assert manager.status("env_flag").source == "env_override"


def test_runtime_override_takes_precedence_over_env(monkeypatch) -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="f", stage=FeatureStage.STABLE, enabled_by_default=False))
    monkeypatch.setenv(f"{ENV_PREFIX}F", "true")
    manager.disable("f")
    assert manager.is_enabled("f") is False
    assert manager.status("f").source == "runtime_override"


def test_list_flags_returns_all_registered() -> None:
    manager = FeatureFlagManager()
    manager.register(FeatureFlag(name="a", stage=FeatureStage.STABLE))
    manager.register(FeatureFlag(name="b", stage=FeatureStage.EXPERIMENTAL))
    names = {status.name for status in manager.list_flags()}
    assert names == {"a", "b"}
