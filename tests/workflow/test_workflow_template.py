"""Built-in template shapes (Phase 17.6)."""

import pytest

from app.workflow.workflow_template import TEMPLATES, build_template
from app.workflow.workflow_validator import validate_template

EXPECTED_TEMPLATES = [
    "Backtest Pipeline", "Optimization Pipeline", "Research Pipeline", "Portfolio Pipeline",
    "Validation Pipeline", "AI Pipeline", "MT5 Preparation Pipeline",
]


def test_all_seven_templates_registered() -> None:
    assert set(TEMPLATES.keys()) == set(EXPECTED_TEMPLATES)


@pytest.mark.parametrize("name", EXPECTED_TEMPLATES)
def test_template_is_structurally_valid(name: str) -> None:
    workflow = build_template(name)
    assert workflow.steps
    assert validate_template(workflow) == []


def test_unknown_template_raises() -> None:
    with pytest.raises(KeyError):
        build_template("Nonexistent Pipeline")
