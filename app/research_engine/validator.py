"""Pre-execution validation for a `ResearchContext`.

Covers: at least one strategy record, no duplicate strategy ids,
identity consistency between each record's `StrategyModel` and
`BacktestResult` (they must reference the same strategy), and version
compatibility of every consumed artifact (`StrategyModel`,
`BacktestResult`, and -- if present -- `OptimizationResult`,
`ValidationResult`, `ReplayResult`).
"""

from dataclasses import dataclass, field

from app.backtesting_engine.metadata import BACKTEST_RESULT_VERSION
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION
from app.replay_engine.metadata import REPLAY_RESULT_VERSION
from app.research_engine.context import ResearchContext, StrategyRecord
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger
from app.validation_engine.metadata import VALIDATION_RESULT_VERSION

logger = get_logger(__name__)


@dataclass
class ResearchIssue:
    """A single validation finding, anchored to a path within the research context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class ResearchCheckResult:
    """Outcome of running `ResearchValidator.validate`.

    Named `ResearchCheckResult`, not `ResearchResult` -- that name is
    reserved for this module's root artifact, the same disambiguation
    precedent `ValidationCheckResult` established in `app.validation_engine`.
    """

    errors: list[ResearchIssue] = field(default_factory=list)
    warnings: list[ResearchIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class ResearchValidator:
    """Validates a `ResearchContext` before any statistics, ranking, or analytics are computed."""

    def validate(self, context: ResearchContext) -> ResearchCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[ResearchIssue] = []
        warnings: list[ResearchIssue] = []

        errors += self._check_records_present(context)
        if not errors:
            errors += self._check_duplicate_strategy_ids(context)
            errors += self._check_identity_consistency(context)
            errors += self._check_versions(context)
            warnings += self._check_recommendations(context)

        result = ResearchCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated research context (%d record(s)): %d error(s), %d warning(s)", len(context.records), len(errors), len(warnings))
        return result

    @staticmethod
    def _check_records_present(context: ResearchContext) -> list[ResearchIssue]:
        if not context.records:
            return [ResearchIssue(path="records", message="At least one StrategyRecord is required.")]
        return []

    @staticmethod
    def _check_duplicate_strategy_ids(context: ResearchContext) -> list[ResearchIssue]:
        errors: list[ResearchIssue] = []
        seen: set[str] = set()
        for record in context.records:
            strategy_id = record.strategy_model.metadata.id
            if strategy_id in seen:
                errors.append(ResearchIssue(path="records", message=f"Duplicate strategy id {strategy_id!r}."))
            seen.add(strategy_id)
        return errors

    @staticmethod
    def _check_identity_consistency(context: ResearchContext) -> list[ResearchIssue]:
        errors: list[ResearchIssue] = []
        for record in context.records:
            strategy_id = record.strategy_model.metadata.id
            if record.backtest_result.metadata.strategy_id != strategy_id:
                errors.append(
                    ResearchIssue(
                        path=f"records[{strategy_id}].backtest_result",
                        message=f"BacktestResult.metadata.strategy_id {record.backtest_result.metadata.strategy_id!r} does not match StrategyModel {strategy_id!r}.",
                    )
                )
        return errors

    @staticmethod
    def _check_versions(context: ResearchContext) -> list[ResearchIssue]:
        errors: list[ResearchIssue] = []
        for record in context.records:
            strategy_id = record.strategy_model.metadata.id

            model_version = record.strategy_model.metadata.model_version
            if model_version != STRATEGY_MODEL_VERSION:
                errors.append(ResearchIssue(path=f"records[{strategy_id}].strategy_model", message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}."))

            backtest_version = record.backtest_result.metadata.result_version
            if backtest_version != BACKTEST_RESULT_VERSION:
                errors.append(ResearchIssue(path=f"records[{strategy_id}].backtest_result", message=f"Unsupported BacktestResult version {backtest_version!r}. Expected {BACKTEST_RESULT_VERSION!r}."))

            if record.optimization_result is not None:
                version = record.optimization_result.metadata.result_version
                if version != OPTIMIZATION_RESULT_VERSION:
                    errors.append(ResearchIssue(path=f"records[{strategy_id}].optimization_result", message=f"Unsupported OptimizationResult version {version!r}. Expected {OPTIMIZATION_RESULT_VERSION!r}."))

            if record.validation_result is not None:
                version = record.validation_result.metadata.result_version
                if version != VALIDATION_RESULT_VERSION:
                    errors.append(ResearchIssue(path=f"records[{strategy_id}].validation_result", message=f"Unsupported ValidationResult version {version!r}. Expected {VALIDATION_RESULT_VERSION!r}."))

            if record.replay_result is not None:
                version = record.replay_result.metadata.result_version
                if version != REPLAY_RESULT_VERSION:
                    errors.append(ResearchIssue(path=f"records[{strategy_id}].replay_result", message=f"Unsupported ReplayResult version {version!r}. Expected {REPLAY_RESULT_VERSION!r}."))
        return errors

    @staticmethod
    def _check_recommendations(context: ResearchContext) -> list[ResearchIssue]:
        warnings: list[ResearchIssue] = []
        if len(context.records) < 2:
            warnings.append(ResearchIssue(path="records", message="Comparison and ranking are most meaningful with 2+ strategies.", severity="warning"))
        return warnings
