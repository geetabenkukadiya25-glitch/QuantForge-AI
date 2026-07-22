"""Shared fixtures for strategy_library tests -- an isolated, temporary
examples/user/state directory triple per test, so nothing ever touches
the real `app/sdl/examples/` or `app/sdl/library/` on disk."""

import shutil
from pathlib import Path

import pytest

from app.strategy_library import StrategyLibraryManager

REAL_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "app" / "sdl" / "examples"


@pytest.fixture
def library_dirs(tmp_path: Path) -> dict[str, Path]:
    examples_dir = tmp_path / "examples"
    user_dir = tmp_path / "library"
    state_dir = tmp_path / "library_state"
    autosave_dir = tmp_path / "autosave"
    examples_dir.mkdir()
    # A real bundled example, copied in, so protection/list/search tests
    # exercise an authentic SDL document (not a synthetic one).
    shutil.copy(REAL_EXAMPLES_DIR / "sma_cross_executable.yaml", examples_dir / "sma_cross_executable.yaml")
    return {
        "root": tmp_path,
        "examples_dir": examples_dir,
        "user_dir": user_dir,
        "state_dir": state_dir,
        "autosave_dir": autosave_dir,
    }


@pytest.fixture
def manager(library_dirs: dict[str, Path]) -> StrategyLibraryManager:
    return StrategyLibraryManager(
        examples_dir=library_dirs["examples_dir"],
        user_dir=library_dirs["user_dir"],
        state_dir=library_dirs["state_dir"],
        autosave_dir=library_dirs["autosave_dir"],
        root=library_dirs["root"],
    )


@pytest.fixture
def example_path(library_dirs: dict[str, Path]) -> Path:
    return library_dirs["examples_dir"] / "sma_cross_executable.yaml"


@pytest.fixture
def minimal_strategy_dict() -> dict:
    return {
        "metadata": {"id": "minimal-strategy", "name": "Minimal Strategy"},
        "market": {"asset_class": "forex"},
        "symbols": ["EURUSD"],
        "timeframes": ["H1"],
    }
