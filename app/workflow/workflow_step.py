"""`WorkflowStep` (Phase 17.6) -- one node in a `Workflow`'s step graph,
plus the `STEP_EXECUTORS` registry that turns a step into the exact
`operation` callable a dashboard's own job-submission closure already
builds, parameterized by `step.parameters` instead of `st.session_state`
widget values.

No engine is ever called outside a Job Manager `operation` closure -- see
`build_operation()` on each executor, which is the only thing
`workflow_runner.py` invokes directly (to build the closure); the closure
itself always runs on the Job Manager's dispatcher thread, exactly like
every dashboard's own `_run_X` closure.
"""

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

from app.workflow.exceptions import StepExecutionError

if TYPE_CHECKING:
    from app.job_manager.job import Job


@dataclass
class WorkflowExecutionContext:
    """Everything a step executor may need to build its `operation`
    closure, resolved fresh per run (never from `st.session_state`) --
    mirrors how each dashboard's own closure captures its registries at
    definition time. Built once per `WorkflowRun` by `WorkflowManager`."""

    dataset_manager: Any
    library_manager: Any
    indicator_registry: Any
    smc_registry: Any
    knowledge_registry: Any = None
    research_registry: Any = None
    portfolio_registry: Any = None
    step_results: dict[str, Any] = field(default_factory=dict)


class StepType(str, Enum):
    DATASET = "DATASET"
    VALIDATION = "VALIDATION"
    COMPILE = "COMPILE"
    BACKTEST = "BACKTEST"
    OPTIMIZATION = "OPTIMIZATION"
    REPLAY = "REPLAY"
    RESEARCH = "RESEARCH"
    PORTFOLIO = "PORTFOLIO"
    KNOWLEDGE_BASE = "KNOWLEDGE_BASE"
    EXTRACTION = "EXTRACTION"
    AI_ASSISTANT = "AI_ASSISTANT"
    EA_GENERATOR = "EA_GENERATOR"
    CUSTOM_PLACEHOLDER = "CUSTOM_PLACEHOLDER"


class StepExecutionState(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
    TIMED_OUT = "TIMED_OUT"


# Which Job Manager `JobCategory` a step type submits under -- resolved
# lazily inside functions that need it (never at import time) so this
# module has no import-time dependency on `app.job_manager` beyond typing.
def job_category_for(step_type: StepType):
    from app.job_manager import JobCategory

    return {
        StepType.VALIDATION: JobCategory.VALIDATION,
        StepType.BACKTEST: JobCategory.BACKTEST,
        StepType.OPTIMIZATION: JobCategory.OPTIMIZATION,
        StepType.REPLAY: JobCategory.REPLAY,
        StepType.RESEARCH: JobCategory.RESEARCH,
        StepType.PORTFOLIO: JobCategory.PORTFOLIO,
        StepType.KNOWLEDGE_BASE: JobCategory.KNOWLEDGE_INDEX,
        StepType.EXTRACTION: JobCategory.EXTRACTION,
        StepType.AI_ASSISTANT: JobCategory.AI_ANALYSIS,
        StepType.EA_GENERATOR: JobCategory.EA_GENERATION,
    }.get(step_type, JobCategory.OTHER)


@dataclass
class WorkflowStep:
    """One node in a `Workflow`. `parameters` is a small JSON-serializable
    dict interpreted by the matching `STEP_EXECUTORS` entry -- e.g. a
    BACKTEST step reads `parameters["sdl_path"]`/`parameters["configuration"]`
    overrides; a step depending on a prior step's result reads
    `parameters["source_step_id"]` (or `source_step_ids` for a
    multi-source step like Portfolio/Research)."""

    type: StepType
    display_name: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    enabled: bool = True
    timeout: float | None = None
    retry_count: int = 0
    continue_on_failure: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)

    # Execution state, filled in by the runner as a run progresses --
    # never persisted as part of the *definition* (see `WorkflowStep.to_dict`
    # excludes it; per-run state lives on `StepResult` in `workflow_models.py`).
    job_id: str | None = field(default=None, compare=False, repr=False)
    execution_state: StepExecutionState = field(default=StepExecutionState.PENDING, compare=False, repr=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "continue_on_failure": self.continue_on_failure,
            "parameters": dict(self.parameters),
        }

    @staticmethod
    def from_dict(data: dict) -> "WorkflowStep":
        return WorkflowStep(
            id=data["id"],
            type=StepType(data["type"]),
            display_name=data["display_name"],
            enabled=data.get("enabled", True),
            timeout=data.get("timeout"),
            retry_count=data.get("retry_count", 0),
            continue_on_failure=data.get("continue_on_failure", False),
            parameters=dict(data.get("parameters", {})),
        )


# --------------------------------------------------------------------------
# Step executors
# --------------------------------------------------------------------------
# Each entry is `(step, context) -> Callable[[Job], Any]`: it resolves
# whatever the step needs (dataset, strategy, prior step results) and
# returns the exact `operation` closure `WorkflowManager`/`WorkflowRunner`
# hands to `JobManager.submit(...)` -- built the same way every dashboard
# already builds its own, just parameterized by the workflow instead of
# widget state. Building the closure never itself calls an engine; only
# invoking the returned closure (from inside a submitted job) does.


def _require(parameters: dict, key: str, step: WorkflowStep):
    if key not in parameters or parameters[key] in (None, ""):
        raise StepExecutionError(f"Step '{step.display_name}' ({step.type.value}) requires parameters['{key}'].")
    return parameters[key]


def _source_result(context: "WorkflowExecutionContext", step: WorkflowStep, key: str = "source_step_id"):
    source_id = _require(step.parameters, key, step)
    if source_id not in context.step_results:
        raise StepExecutionError(f"Step '{step.display_name}' references source step '{source_id}', which has not produced a result yet.")
    return context.step_results[source_id]


def _dataset_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    dataset_id = _require(step.parameters, "dataset_id", step)

    def _op(job: "Job") -> Any:
        record = context.dataset_manager.get(dataset_id)
        df = context.dataset_manager.load_dataframe(dataset_id)
        context.dataset_manager.record_used(dataset_id)
        return {"record": record, "dataframe": df}

    return _op


def _validation_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    """Reuses `DatasetManager.revalidate` (dataset-quality validation) --
    the same "Validate" action `19_Dataset_Manager.py` exposes."""
    dataset_id = _require(step.parameters, "dataset_id", step)

    def _op(job: "Job") -> Any:
        result, health = context.dataset_manager.revalidate(dataset_id)
        return {"result": result, "health": health}

    return _op


def _compile_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    """Reuses `StrategyLibraryManager.load_definition` + `StrategyBuilder`,
    exactly as `8_Backtesting_Dashboard.py` does when it builds `model`."""
    state_key = _require(step.parameters, "strategy_state_key", step)

    def _op(job: "Job") -> Any:
        from app.strategy_builder import StrategyBuilder, StrategyContext

        path = context.library_manager.path_from_state_key(state_key)
        definition = context.library_manager.load_definition(path)
        build_result = StrategyBuilder().try_build(
            StrategyContext(sdl_definition=definition, indicator_registry=context.indicator_registry, smc_registry=context.smc_registry)
        )
        if not build_result.is_valid:
            raise StepExecutionError(f"Strategy Builder rejected '{state_key}': {build_result.validation.report()}")
        return build_result.model

    return _op


def _backtest_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.backtesting_engine import BacktestConfiguration, BacktestingEngine
        from app.indicator_engine import IndicatorEngine
        from app.smart_money_engine import SmartMoneyEngine

        model = _source_result(context, step, "strategy_step_id")
        dataset = _source_result(context, step, "dataset_step_id")
        df = dataset["dataframe"] if isinstance(dataset, dict) else dataset
        record = dataset.get("record") if isinstance(dataset, dict) else None
        overrides = dict(step.parameters.get("configuration", {}))
        configuration = BacktestConfiguration(
            symbol=overrides.pop("symbol", (record.symbol if record else None) or "UNKNOWN"),
            timeframe=overrides.pop("timeframe", (record.timeframe if record else None) or "UNKNOWN"),
            **overrides,
        )
        engine = BacktestingEngine(
            indicator_engine=IndicatorEngine(registry=context.indicator_registry),
            smart_money_engine=SmartMoneyEngine(registry=context.smc_registry),
        )
        return engine.try_execute(model, df, configuration, progress_callback=job.progress.make_progress_callback(job))

    return _op


def _optimization_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.optimization_engine import OptimizationConfiguration, OptimizationEngine, ParameterDefinition, ParameterSpace

        model = _source_result(context, step, "strategy_step_id")
        dataset = _source_result(context, step, "dataset_step_id")
        df = dataset["dataframe"] if isinstance(dataset, dict) else dataset
        record = dataset.get("record") if isinstance(dataset, dict) else None
        base_conf_overrides = dict(step.parameters.get("base_configuration", {}))
        base_configuration = _import_backtest_configuration(base_conf_overrides, record)
        definitions = tuple(ParameterDefinition(**d) for d in step.parameters.get("parameter_definitions", []))
        parameter_space = ParameterSpace(definitions=definitions)
        opt_params = dict(step.parameters.get("optimization_configuration", {}))
        opt_params.setdefault("strategy_id", model.metadata.id)
        opt_params.setdefault("symbol", base_configuration.symbol)
        opt_params.setdefault("timeframe", base_configuration.timeframe)
        opt_params.setdefault("search_method", "GRID")
        opt_params.setdefault("objective", "NET_PROFIT")
        optimization_configuration = OptimizationConfiguration(**opt_params)
        return OptimizationEngine().try_execute(model, df, base_configuration, parameter_space, optimization_configuration)

    return _op


def _import_backtest_configuration(overrides: dict, record):
    from app.backtesting_engine import BacktestConfiguration

    overrides = dict(overrides)
    symbol = overrides.pop("symbol", (record.symbol if record else None) or "UNKNOWN")
    timeframe = overrides.pop("timeframe", (record.timeframe if record else None) or "UNKNOWN")
    return BacktestConfiguration(symbol=symbol, timeframe=timeframe, **overrides)


def _replay_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.replay_engine import ReplayConfiguration, ReplayEngine
        from app.indicator_engine import IndicatorEngine
        from app.smart_money_engine import SmartMoneyEngine

        dataset = _source_result(context, step, "dataset_step_id")
        df = dataset["dataframe"] if isinstance(dataset, dict) else dataset
        record = dataset.get("record") if isinstance(dataset, dict) else None
        model = context.step_results.get(step.parameters.get("strategy_step_id"))
        backtest_session = context.step_results.get(step.parameters.get("backtest_step_id"))
        backtest_result = backtest_session.result if backtest_session is not None and hasattr(backtest_session, "result") else None
        overrides = dict(step.parameters.get("configuration", {}))
        configuration = ReplayConfiguration(
            symbol=overrides.pop("symbol", (record.symbol if record else None) or "UNKNOWN"),
            timeframe=overrides.pop("timeframe", (record.timeframe if record else None) or "UNKNOWN"),
            **overrides,
        )
        return ReplayEngine().try_execute(
            df,
            configuration,
            strategy_model=model,
            indicator_engine=IndicatorEngine(registry=context.indicator_registry) if model is not None else None,
            smart_money_engine=SmartMoneyEngine(registry=context.smc_registry) if model is not None else None,
            backtest_result=backtest_result,
        )

    return _op


def _research_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.research_engine import ResearchConfiguration, ResearchEngine
        from app.research_engine.context import StrategyRecord

        records = []
        for source_id in _require(step.parameters, "backtest_step_ids", step):
            model = context.step_results.get(step.parameters.get("strategy_step_id"))
            session = context.step_results[source_id]
            records.append(StrategyRecord(strategy_model=model, backtest_result=session.result))
        configuration = ResearchConfiguration(**step.parameters.get("configuration", {}))
        return ResearchEngine().try_execute(tuple(records), configuration)

    return _op


def _portfolio_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.portfolio_engine import PortfolioConfiguration, PortfolioManagementEngine
        from app.portfolio_engine.context import PortfolioStrategyEntry

        entries = []
        for source_id in _require(step.parameters, "backtest_step_ids", step):
            model = context.step_results.get(step.parameters.get("strategy_step_id"))
            session = context.step_results[source_id]
            entries.append(PortfolioStrategyEntry(strategy_model=model, backtest_result=session.result))
        configuration = PortfolioConfiguration(**step.parameters.get("configuration", {}))
        return PortfolioManagementEngine().try_execute(tuple(entries), configuration)

    return _op


def _knowledge_base_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.knowledge_base import KnowledgeConfiguration, KnowledgeBaseEngine, KnowledgeEntry

        raw_entries = _require(step.parameters, "entries", step)
        entries = tuple(KnowledgeEntry(**e) for e in raw_entries)
        configuration = KnowledgeConfiguration(**step.parameters.get("configuration", {}))
        return KnowledgeBaseEngine().try_execute(entries, configuration, indicator_registry=context.indicator_registry, smc_registry=context.smc_registry)

    return _op


def _extraction_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.ai_extraction import ExtractionConfiguration, AIStrategyExtractionEngine, SourceType

        raw_text = _require(step.parameters, "raw_text", step)
        source_type = SourceType(step.parameters.get("source_type", "PLAIN_TEXT"))
        configuration = ExtractionConfiguration(**step.parameters.get("configuration", {}))
        return AIStrategyExtractionEngine().try_execute(raw_text, source_type, configuration, indicator_registry=context.indicator_registry, smc_registry=context.smc_registry)

    return _op


def _ai_assistant_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.ai_assistant import AIResearchAssistantEngine, AssistantConfiguration

        query = _require(step.parameters, "query", step)
        configuration = AssistantConfiguration(**step.parameters.get("configuration", {}))
        return AIResearchAssistantEngine().try_execute(
            query,
            configuration=configuration,
            knowledge_registry=context.knowledge_registry,
            research_registry=context.research_registry,
            portfolio_registry=context.portfolio_registry,
            indicator_registry=context.indicator_registry,
            smc_registry=context.smc_registry,
        )

    return _op


def _ea_generator_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    def _op(job: "Job") -> Any:
        from app.ea_generator import EAGeneratorConfiguration, EAGeneratorEngine

        model = _source_result(context, step, "strategy_step_id")
        configuration = EAGeneratorConfiguration(**step.parameters.get("configuration", {}))
        return EAGeneratorEngine().try_execute(model, configuration)

    return _op


def _custom_placeholder_executor(step: WorkflowStep, context: "WorkflowExecutionContext") -> Callable[["Job"], Any]:
    """An honest no-op -- per the spec's "Do not fabricate workflow
    success," a CUSTOM_PLACEHOLDER step always reports that it isn't
    implemented rather than pretending to have done something."""

    def _op(job: "Job") -> Any:
        return {"status": "NOT_IMPLEMENTED", "message": f"Custom step '{step.display_name}' has no executor wired up yet."}

    return _op


STEP_EXECUTORS: dict[StepType, Callable[[WorkflowStep, "WorkflowExecutionContext"], Callable[["Job"], Any]]] = {
    StepType.DATASET: _dataset_executor,
    StepType.VALIDATION: _validation_executor,
    StepType.COMPILE: _compile_executor,
    StepType.BACKTEST: _backtest_executor,
    StepType.OPTIMIZATION: _optimization_executor,
    StepType.REPLAY: _replay_executor,
    StepType.RESEARCH: _research_executor,
    StepType.PORTFOLIO: _portfolio_executor,
    StepType.KNOWLEDGE_BASE: _knowledge_base_executor,
    StepType.EXTRACTION: _extraction_executor,
    StepType.AI_ASSISTANT: _ai_assistant_executor,
    StepType.EA_GENERATOR: _ea_generator_executor,
    StepType.CUSTOM_PLACEHOLDER: _custom_placeholder_executor,
}
