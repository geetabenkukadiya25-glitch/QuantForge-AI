"""Pure structural validation for a `Workflow` definition (Phase 17.6):
cycles, missing/duplicate step ids, broken dependency references, and
state-transition legality. Never touches disk, Job Manager, or an engine.
"""

from app.workflow.workflow_models import Workflow, WorkflowStatus, is_valid_transition
from app.workflow.workflow_step import WorkflowStep

__all__ = [
    "detect_cycles",
    "find_duplicate_ids",
    "find_missing_steps",
    "find_broken_dependencies",
    "validate_template",
    "is_valid_transition",
]


def find_duplicate_ids(steps: list[WorkflowStep]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for step in steps:
        if step.id in seen:
            duplicates.append(step.id)
        seen.add(step.id)
    return duplicates


def find_missing_steps(steps: list[WorkflowStep], dependencies: dict[str, list[str]]) -> list[str]:
    """Dependency KEYS that don't correspond to any declared step."""
    step_ids = {s.id for s in steps}
    return [step_id for step_id in dependencies if step_id not in step_ids]


def find_broken_dependencies(steps: list[WorkflowStep], dependencies: dict[str, list[str]]) -> list[tuple[str, str]]:
    """`(step_id, missing_dependency_id)` pairs -- a dependency VALUE that
    doesn't correspond to any declared step."""
    step_ids = {s.id for s in steps}
    broken: list[tuple[str, str]] = []
    for step_id, deps in dependencies.items():
        for dep in deps:
            if dep not in step_ids:
                broken.append((step_id, dep))
    return broken


def detect_cycles(steps: list[WorkflowStep], dependencies: dict[str, list[str]]) -> list[str] | None:
    """Returns the step-id sequence of one cycle if the dependency graph
    isn't a DAG, else `None`. Standard white/gray/black DFS."""
    step_ids = [s.id for s in steps]
    color: dict[str, int] = {sid: 0 for sid in step_ids}  # 0=white 1=gray 2=black
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        color[node] = 1
        path.append(node)
        for dep in dependencies.get(node, []):
            if dep not in color:
                continue  # broken dependency, reported separately
            if color[dep] == 1:
                cycle_start = path.index(dep)
                return path[cycle_start:] + [dep]
            if color[dep] == 0:
                found = visit(dep)
                if found is not None:
                    return found
        path.pop()
        color[node] = 2
        return None

    for sid in step_ids:
        if color[sid] == 0:
            found = visit(sid)
            if found is not None:
                return found
    return None


def validate_template(workflow: Workflow) -> list[str]:
    """All structural issues for `workflow`, as human-readable strings.
    Empty list means the workflow is structurally sound (does not check
    whether individual step parameters are runnable -- that's discovered
    at execution time, per-step, same as any dashboard's own validation)."""
    issues: list[str] = []

    duplicates = find_duplicate_ids(workflow.steps)
    if duplicates:
        issues.append(f"Duplicate step id(s): {', '.join(sorted(set(duplicates)))}")

    missing = find_missing_steps(workflow.steps, workflow.dependencies)
    if missing:
        issues.append(f"Dependencies declared for unknown step id(s): {', '.join(missing)}")

    broken = find_broken_dependencies(workflow.steps, workflow.dependencies)
    if broken:
        issues.append("; ".join(f"Step '{step_id}' depends on unknown step '{dep}'" for step_id, dep in broken))

    cycle = detect_cycles(workflow.steps, workflow.dependencies)
    if cycle:
        issues.append(f"Cycle detected: {' -> '.join(cycle)}")

    if not workflow.steps:
        issues.append("Workflow has no steps.")

    return issues
