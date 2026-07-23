"""`topological_order`/`build_tree` (Phase 17.6)."""

import pytest

from app.workflow.exceptions import WorkflowValidationError
from app.workflow.workflow_graph import build_tree, topological_order
from app.workflow.workflow_step import StepType, WorkflowStep


def _step(step_id: str) -> WorkflowStep:
    return WorkflowStep(id=step_id, type=StepType.CUSTOM_PLACEHOLDER, display_name=step_id)


def test_topological_order_linear() -> None:
    a, b, c = _step("a"), _step("b"), _step("c")
    order = topological_order([a, b, c], {"b": ["a"], "c": ["b"]})
    assert order == ["a", "b", "c"]


def test_topological_order_raises_on_cycle() -> None:
    a, b = _step("a"), _step("b")
    with pytest.raises(WorkflowValidationError):
        topological_order([a, b], {"a": ["b"], "b": ["a"]})


def test_build_tree_linear_chain() -> None:
    a, b, c = _step("a"), _step("b"), _step("c")
    tree = build_tree([a, b, c], {"b": ["a"], "c": ["b"]})
    assert len(tree) == 1
    assert tree[0]["step"].id == "a"
    assert tree[0]["children"][0]["step"].id == "b"
    assert tree[0]["children"][0]["children"][0]["step"].id == "c"


def test_build_tree_branching() -> None:
    a, b, c = _step("a"), _step("b"), _step("c")
    tree = build_tree([a, b, c], {"b": ["a"], "c": ["a"]})
    assert len(tree) == 1
    child_ids = {child["step"].id for child in tree[0]["children"]}
    assert child_ids == {"b", "c"}
