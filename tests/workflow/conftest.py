"""Shared fixtures for `app.workflow` tests -- an isolated, temporary
state directory per test, plus a tmp-scoped execution context (real
`DatasetManager`/`StrategyLibraryManager`/registries pointed at `tmp_path`,
never the real on-disk registry/state) so nothing here ever touches real
project state."""

from pathlib import Path

import pytest

from app.dataset_manager import DatasetManager
from app.strategy_library import StrategyLibraryManager
from app.workflow.workflow_manager import WorkflowManager
from app.workflow.workflow_step import WorkflowExecutionContext

VALID_CSV = (
    b"Date,Time,Open,High,Low,Close,Volume,Spread\n"
    b"2024.01.01,00:00,1.1000,1.1010,1.0990,1.1005,50,2\n"
    b"2024.01.01,01:00,1.1005,1.1020,1.1000,1.1015,60,2\n"
    b"2024.01.01,02:00,1.1015,1.1025,1.1005,1.1010,55,2\n"
    b"2024.01.01,03:00,1.1010,1.1030,1.1000,1.1025,90,45\n"
)

EXECUTABLE_SDL_PATH = Path(__file__).resolve().parents[2] / "app" / "sdl" / "examples" / "sma_cross_executable.yaml"


@pytest.fixture
def dataset_manager(tmp_path: Path) -> DatasetManager:
    return DatasetManager(registry_dir=tmp_path / "dm_registry", state_dir=tmp_path / "dm_state")


@pytest.fixture
def library_manager(tmp_path: Path) -> StrategyLibraryManager:
    return StrategyLibraryManager(
        user_dir=tmp_path / "sdl_user", state_dir=tmp_path / "sdl_state", autosave_dir=tmp_path / "sdl_autosave"
    )


@pytest.fixture
def execution_context(dataset_manager: DatasetManager, library_manager: StrategyLibraryManager) -> WorkflowExecutionContext:
    from app.indicator_engine import IndicatorRegistry
    from app.smart_money_engine import SMCRegistry

    indicator_registry = IndicatorRegistry()
    indicator_registry.register_builtins()
    smc_registry = SMCRegistry()
    smc_registry.register_builtins()
    return WorkflowExecutionContext(
        dataset_manager=dataset_manager, library_manager=library_manager,
        indicator_registry=indicator_registry, smc_registry=smc_registry,
    )


@pytest.fixture
def manager(tmp_path: Path, execution_context: WorkflowExecutionContext) -> WorkflowManager:
    return WorkflowManager(state_dir=tmp_path / "wf_state", context_factory=lambda: execution_context)


@pytest.fixture
def valid_csv_bytes() -> bytes:
    return VALID_CSV


@pytest.fixture
def executable_strategy_state_key(library_manager: StrategyLibraryManager) -> str:
    return library_manager.state_key(EXECUTABLE_SDL_PATH)
