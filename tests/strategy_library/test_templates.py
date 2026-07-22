"""Every strategy template builds a schema-valid `StrategyDefinition`
through the unmodified SDL models -- no schema changes, no parser changes."""

import pytest

from app.sdl.validator import StrategyValidator
from app.strategy_library import StrategyLibraryManager, list_template_names
from app.strategy_library.templates import build_template


@pytest.mark.parametrize("template_name", list_template_names())
def test_every_template_builds_a_valid_definition(template_name: str) -> None:
    definition = build_template(template_name, "test-id", "Test Name", "Test Author")
    result = StrategyValidator().validate(definition)
    assert result.is_valid, result.report()


def test_list_template_names_covers_the_required_seventeen() -> None:
    names = list_template_names()
    assert len(names) == 17
    for required in ("SMA Crossover", "ICT Liquidity Sweep", "SMC BOS + CHOCH", "Blank Strategy"):
        assert required in names


def test_unknown_template_name_raises_key_error() -> None:
    with pytest.raises(KeyError):
        build_template("Not A Real Template", "id", "name")


def test_new_strategy_from_template_saves_into_user_library(manager: StrategyLibraryManager, library_dirs: dict) -> None:
    path = manager.new_strategy_from_template("SMA Crossover", "sma_from_template.yaml", "SMA From Template")
    assert path.parent == library_dirs["user_dir"]
    definition = manager.load_definition(path)
    assert definition.indicators
    assert definition.entry_rules
