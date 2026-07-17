"""Tests for SDL version compatibility checks."""

from app.sdl.version import SUPPORTED_SDL_VERSIONS
from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.exceptions import StrategyValidationError


def test_supported_sdl_version_builds(context_factory) -> None:
    context = context_factory(metadata={"id": "x", "name": "X", "sdl_version": SUPPORTED_SDL_VERSIONS[0]})
    model = StrategyBuilder().build(context)
    assert model.metadata.sdl_version == SUPPORTED_SDL_VERSIONS[0]


def test_unsupported_sdl_version_raises(context_factory) -> None:
    context = context_factory(metadata={"id": "x", "name": "X", "sdl_version": "999.0.0"})
    try:
        StrategyBuilder().build(context)
        assert False, "expected StrategyValidationError"
    except StrategyValidationError as exc:
        assert any("sdl_version" in issue.path for issue in exc.issues)


def test_model_carries_sdl_version_forward(context_factory) -> None:
    context = context_factory(metadata={"id": "x", "name": "X", "sdl_version": SUPPORTED_SDL_VERSIONS[0]})
    model = StrategyBuilder().build(context)
    assert model.metadata.sdl_version == SUPPORTED_SDL_VERSIONS[0]
    assert model.metadata.model_version  # this module's own schema version is also stamped
