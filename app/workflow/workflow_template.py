"""Built-in workflow templates (Phase 17.6) -- skeleton `Workflow`s with
steps wired sequentially via `dependencies`, parameters left blank for the
user to fill in (dataset id, strategy state key, ...) via the Workflow
Editor before running. Never pre-fills a fabricated dataset/strategy."""

from typing import Callable

from app.workflow.workflow_models import Workflow
from app.workflow.workflow_step import StepType, WorkflowStep


def _linear(name: str, description: str, step_types: list[tuple[StepType, str]]) -> Workflow:
    steps = [WorkflowStep(type=t, display_name=label) for t, label in step_types]
    dependencies = {steps[i].id: [steps[i - 1].id] for i in range(1, len(steps))}
    return Workflow(name=name, description=description, steps=steps, dependencies=dependencies, template_name=name)


def backtest_pipeline() -> Workflow:
    return _linear(
        "Backtest Pipeline",
        "Dataset -> Compile Strategy -> Backtest.",
        [(StepType.DATASET, "Dataset"), (StepType.COMPILE, "Compile Strategy"), (StepType.BACKTEST, "Backtest")],
    )


def optimization_pipeline() -> Workflow:
    return _linear(
        "Optimization Pipeline",
        "Dataset -> Compile Strategy -> Optimization.",
        [(StepType.DATASET, "Dataset"), (StepType.COMPILE, "Compile Strategy"), (StepType.OPTIMIZATION, "Optimization")],
    )


def research_pipeline() -> Workflow:
    return _linear(
        "Research Pipeline",
        "Dataset -> Compile Strategy -> Backtest -> Research.",
        [(StepType.DATASET, "Dataset"), (StepType.COMPILE, "Compile Strategy"), (StepType.BACKTEST, "Backtest"), (StepType.RESEARCH, "Research")],
    )


def portfolio_pipeline() -> Workflow:
    return _linear(
        "Portfolio Pipeline",
        "Dataset -> Backtest -> Portfolio -> Export Report.",
        [(StepType.DATASET, "Dataset"), (StepType.COMPILE, "Compile Strategy"), (StepType.BACKTEST, "Backtest"), (StepType.PORTFOLIO, "Portfolio")],
    )


def validation_pipeline() -> Workflow:
    return _linear(
        "Validation Pipeline",
        "Dataset -> Compile Strategy -> Backtest -> Optimization -> Validation.",
        [
            (StepType.DATASET, "Dataset"),
            (StepType.COMPILE, "Compile Strategy"),
            (StepType.BACKTEST, "Backtest"),
            (StepType.OPTIMIZATION, "Optimization"),
            (StepType.VALIDATION, "Validation"),
        ],
    )


def ai_pipeline() -> Workflow:
    return _linear(
        "AI Pipeline",
        "Dataset -> Extraction -> Knowledge Base -> AI Assistant.",
        [(StepType.DATASET, "Dataset"), (StepType.EXTRACTION, "Extraction"), (StepType.KNOWLEDGE_BASE, "Knowledge Base"), (StepType.AI_ASSISTANT, "AI Assistant")],
    )


def mt5_preparation_pipeline() -> Workflow:
    return _linear(
        "MT5 Preparation Pipeline",
        "Dataset -> Compile Strategy -> Backtest -> EA Generator.",
        [(StepType.DATASET, "Dataset"), (StepType.COMPILE, "Compile Strategy"), (StepType.BACKTEST, "Backtest"), (StepType.EA_GENERATOR, "EA Generator")],
    )


TEMPLATES: dict[str, Callable[[], Workflow]] = {
    "Backtest Pipeline": backtest_pipeline,
    "Optimization Pipeline": optimization_pipeline,
    "Research Pipeline": research_pipeline,
    "Portfolio Pipeline": portfolio_pipeline,
    "Validation Pipeline": validation_pipeline,
    "AI Pipeline": ai_pipeline,
    "MT5 Preparation Pipeline": mt5_preparation_pipeline,
}


def build_template(template_name: str) -> Workflow:
    try:
        factory = TEMPLATES[template_name]
    except KeyError as exc:
        raise KeyError(f"Unknown workflow template '{template_name}'.") from exc
    return factory()
