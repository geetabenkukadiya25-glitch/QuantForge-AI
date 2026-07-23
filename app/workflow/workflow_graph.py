"""Pure dependency-graph helpers (Phase 17.6): topological ordering for
the runner, and a nested-dict tree for the pure-Streamlit collapsible
"Dependency Graph" view (no custom JS -- `st.expander` + indentation
consumes `build_tree`'s output directly).
"""

from app.workflow.exceptions import WorkflowValidationError
from app.workflow.workflow_step import WorkflowStep
from app.workflow.workflow_validator import detect_cycles


def topological_order(steps: list[WorkflowStep], dependencies: dict[str, list[str]]) -> list[str]:
    """Kahn's algorithm. Raises `WorkflowValidationError` if the graph has
    a cycle (surfacing the exact cycle `detect_cycles` found)."""
    cycle = detect_cycles(steps, dependencies)
    if cycle is not None:
        raise WorkflowValidationError([f"Cycle detected: {' -> '.join(cycle)}"])

    step_ids = [s.id for s in steps]
    in_degree = {sid: 0 for sid in step_ids}
    for sid, deps in dependencies.items():
        if sid in in_degree:
            in_degree[sid] = len([d for d in deps if d in in_degree])

    # Stable order: process in declaration order among ties, so a plain
    # sequential workflow (each step depending only on its predecessor)
    # keeps its authored order.
    remaining = list(step_ids)
    resolved: list[str] = []
    resolved_set: set[str] = set()

    while remaining:
        ready = [sid for sid in remaining if all(d in resolved_set or d not in in_degree for d in dependencies.get(sid, []))]
        if not ready:
            # Shouldn't happen once `detect_cycles` passed, but never loop forever.
            raise WorkflowValidationError(["Unable to resolve step order (unexpected dependency state)."])
        next_id = ready[0]
        resolved.append(next_id)
        resolved_set.add(next_id)
        remaining.remove(next_id)

    return resolved


def build_tree(steps: list[WorkflowStep], dependencies: dict[str, list[str]]) -> list[dict]:
    """A forest of `{"step": WorkflowStep, "children": [...]}` nodes --
    roots are steps with no dependency, matching the spec's linear
    "Dataset -> Strategy -> Backtest -> ..." diagram shape when the
    workflow is sequential, and branching naturally for a DAG."""
    by_id = {s.id: s for s in steps}
    children_of: dict[str, list[str]] = {sid: [] for sid in by_id}
    for step_id, deps in dependencies.items():
        for dep in deps:
            if dep in children_of:
                children_of[dep].append(step_id)

    has_dependency = {sid for sid, deps in dependencies.items() if deps}
    roots = [sid for sid in by_id if sid not in has_dependency]

    def node(step_id: str, visited: frozenset[str]) -> dict:
        if step_id in visited:
            return {"step": by_id[step_id], "children": []}  # guard against a cycle slipping through
        child_ids = children_of.get(step_id, [])
        return {"step": by_id[step_id], "children": [node(c, visited | {step_id}) for c in child_ids]}

    return [node(root_id, frozenset()) for root_id in roots]
