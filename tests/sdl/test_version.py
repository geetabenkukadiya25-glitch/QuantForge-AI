"""Tests for VersionManager and SemVer."""

import pytest

from app.sdl.exceptions import SDLVersionError
from app.sdl.version import SemVer, VersionManager


def test_is_supported_true_for_known_version() -> None:
    assert VersionManager().is_supported("1.0.0") is True


def test_is_supported_false_for_unknown_version() -> None:
    assert VersionManager().is_supported("2.0.0") is False


def test_compare_versions() -> None:
    manager = VersionManager(supported_versions=["1.0.0", "1.1.0"])
    assert manager.compare("1.0.0", "1.1.0") == -1
    assert manager.compare("1.1.0", "1.0.0") == 1
    assert manager.compare("1.0.0", "1.0.0") == 0


def test_latest_supported() -> None:
    manager = VersionManager(supported_versions=["1.0.0", "1.2.0", "1.1.0"])
    assert manager.latest_supported() == "1.2.0"


def test_migrate_same_version_is_noop() -> None:
    data = {"a": 1}
    result = VersionManager().migrate(data, "1.0.0", "1.0.0")
    assert result is data


def test_migrate_unsupported_source_raises() -> None:
    with pytest.raises(SDLVersionError):
        VersionManager().migrate({}, "0.9.0", "1.0.0")


def test_migrate_cross_version_not_yet_available_raises() -> None:
    manager = VersionManager(supported_versions=["1.0.0", "2.0.0"])
    with pytest.raises(SDLVersionError):
        manager.migrate({}, "1.0.0", "2.0.0")


def test_semver_parse_invalid_raises() -> None:
    with pytest.raises(SDLVersionError):
        SemVer.parse("not-a-version")


def test_semver_ordering() -> None:
    assert SemVer.parse("1.0.0") < SemVer.parse("1.0.1")
    assert SemVer.parse("1.2.0") < SemVer.parse("2.0.0")
