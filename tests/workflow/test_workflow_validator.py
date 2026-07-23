"""Cycle/duplicate/broken-dependency detection (Phase 17.6)."""

from app.workflow.workflow_models import Workflow
from app.workflow.workflow_step import StepType, WorkflowStep
from app.workflow.workflow_validator import (
    detect_cycles,
    find_broken_dependencies,
    find_duplicate_ids,
    find_missing_steps,
    validate_template,
)


def _step(step_id: str) -> WorkflowStep:
    return WorkflowStep(id=step_id, type=StepType.CUSTOM_PLACEHOLDER, display_name=step_id)


def test_find_duplicate_ids() -> None:
    a, b = _step("a"), _step("a")
    assert find_duplicate_ids([a, b]) == ["a"]


def test_find_missing_steps() -> None:
    a = _step("a")
    assert find_missing_steps([a], {"ghost": ["a"]}) == ["ghost"]


def test_find_broken_dependencies() -> None:
    a = _step("a")
    assert find_broken_dependencies([a], {"a": ["ghost"]}) == [("a", "ghost")]


def test_detect_cycles_none_for_dag() -> None:
    a, b, c = _step("a"), _step("b"), _step("c")
    assert detect_cycles([a, b, c], {"b": ["a"], "c": ["b"]}) is None


def test_detect_cycles_finds_cycle() -> None:
    a, b = _step("a"), _step("b")
    cycle = detect_cycles([a, b], {"a": ["b"], "b": ["a"]})
    assert cycle is not None
    assert set(cycle) == {"a", "b"}


def test_validate_template_reports_all_issues() -> None:
    a, a2 = _step("a"), _step("a")
    workflow = Workflow(name="Bad", steps=[a, a2], dependencies={"a": ["ghost"]})
    issues = validate_template(workflow)
    assert any("Duplicate" in i for i in issues)
    assert any("unknown step" in i for i in issues)


def test_validate_template_empty_steps() -> None:
    workflow = Workflow(name="Empty", steps=[])
    issues = validate_template(workflow)
    assert any("no steps" in i for i in issues)


def test_validate_template_clean_workflow_has_no_issues() -> None:
    a, b = _step("a"), _step("b")
    workflow = Workflow(name="Clean", steps=[a, b], dependencies={"b": ["a"]})
    assert validate_template(workflow) == []
