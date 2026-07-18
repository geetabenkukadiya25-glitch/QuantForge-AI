"""Pre-execution validation for a `PortfolioContext`.

Covers: at least `configuration.min_strategies_required` entries, no
duplicate strategy ids, identity consistency between each entry's
`StrategyModel` and `BacktestResult` (they must reference the same
strategy), and version compatibility of every consumed artifact
(`StrategyModel`, `BacktestResult`, and -- if present -- `OptimizationResult`,
`ValidationResult`, `ReplayResult`, `ResearchResult`).
"""

from dataclasses import dataclass, field

from app.backtesting_engine.metadata import BACKTEST_RESULT_VERSION
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION
from app.portfolio_engine.context import PortfolioContext
from app.portfolio_engine.models import AllocationMethod
from app.replay_engine.metadata import REPLAY_RESULT_VERSION
from app.research_engine.metadata import RESEARCH_RESULT_VERSION
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger
from app.validation_engine.metadata import VALIDATION_RESULT_VERSION

logger = get_logger(__name__)


@dataclass
class PortfolioIssue:
    """A single validation finding, anchored to a path within the portfolio context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class PortfolioCheckResult:
    """Outcome of running `PortfolioValidator.validate`.

    Named `PortfolioCheckResult`, not `PortfolioResult` -- that name is
    reserved for this module's root artifact, the same disambiguation
    precedent `ValidationCheckResult`/`ResearchCheckResult`/
    `ExtractionCheckResult` established.
    """

    errors: list[PortfolioIssue] = field(default_factory=list)
    warnings: list[PortfolioIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class PortfolioValidator:
    """Validates a `PortfolioContext` before any allocation, statistics, or analytics are computed."""

    def validate(self, context: PortfolioContext) -> PortfolioCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[PortfolioIssue] = []
        warnings: list[PortfolioIssue] = []

        errors += self._check_minimum_entries(context)
        if not errors:
            errors += self._check_duplicate_strategy_ids(context)
            errors += self._check_identity_consistency(context)
            errors += self._check_versions(context)
            warnings += self._check_manual_weights(context)
            warnings += self._check_diversification(context)

        result = PortfolioCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated portfolio context (%d entry(ies)): %d error(s), %d warning(s)", len(context.entries), len(errors), len(warnings))
        return result

    @staticmethod
    def _check_minimum_entries(context: PortfolioContext) -> list[PortfolioIssue]:
        required = context.configuration.min_strategies_required
        if len(context.entries) < required:
            return [PortfolioIssue(path="entries", message=f"At least {required} strategy(ies) are required; got {len(context.entries)}.")]
        return []

    @staticmethod
    def _check_duplicate_strategy_ids(context: PortfolioContext) -> list[PortfolioIssue]:
        errors: list[PortfolioIssue] = []
        seen: set[str] = set()
        for entry in context.entries:
            strategy_id = entry.strategy_model.metadata.id
            if strategy_id in seen:
                errors.append(PortfolioIssue(path="entries", message=f"Duplicate strategy id {strategy_id!r}."))
            seen.add(strategy_id)
        return errors

    @staticmethod
    def _check_identity_consistency(context: PortfolioContext) -> list[PortfolioIssue]:
        errors: list[PortfolioIssue] = []
        for entry in context.entries:
            strategy_id = entry.strategy_model.metadata.id
            if entry.backtest_result.metadata.strategy_id != strategy_id:
                errors.append(
                    PortfolioIssue(
                        path=f"entries[{strategy_id}].backtest_result",
                        message=f"BacktestResult.metadata.strategy_id {entry.backtest_result.metadata.strategy_id!r} does not match StrategyModel {strategy_id!r}.",
                    )
                )
        return errors

    @staticmethod
    def _check_versions(context: PortfolioContext) -> list[PortfolioIssue]:
        errors: list[PortfolioIssue] = []
        for entry in context.entries:
            strategy_id = entry.strategy_model.metadata.id

            model_version = entry.strategy_model.metadata.model_version
            if model_version != STRATEGY_MODEL_VERSION:
                errors.append(PortfolioIssue(path=f"entries[{strategy_id}].strategy_model", message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}."))

            backtest_version = entry.backtest_result.metadata.result_version
            if backtest_version != BACKTEST_RESULT_VERSION:
                errors.append(PortfolioIssue(path=f"entries[{strategy_id}].backtest_result", message=f"Unsupported BacktestResult version {backtest_version!r}. Expected {BACKTEST_RESULT_VERSION!r}."))

            if entry.optimization_result is not None:
                version = entry.optimization_result.metadata.result_version
                if version != OPTIMIZATION_RESULT_VERSION:
                    errors.append(PortfolioIssue(path=f"entries[{strategy_id}].optimization_result", message=f"Unsupported OptimizationResult version {version!r}. Expected {OPTIMIZATION_RESULT_VERSION!r}."))

            if entry.validation_result is not None:
                version = entry.validation_result.metadata.result_version
                if version != VALIDATION_RESULT_VERSION:
                    errors.append(PortfolioIssue(path=f"entries[{strategy_id}].validation_result", message=f"Unsupported ValidationResult version {version!r}. Expected {VALIDATION_RESULT_VERSION!r}."))

            if entry.replay_result is not None:
                version = entry.replay_result.metadata.result_version
                if version != REPLAY_RESULT_VERSION:
                    errors.append(PortfolioIssue(path=f"entries[{strategy_id}].replay_result", message=f"Unsupported ReplayResult version {version!r}. Expected {REPLAY_RESULT_VERSION!r}."))

            if entry.research_result is not None:
                version = entry.research_result.metadata.result_version
                if version != RESEARCH_RESULT_VERSION:
                    errors.append(PortfolioIssue(path=f"entries[{strategy_id}].research_result", message=f"Unsupported ResearchResult version {version!r}. Expected {RESEARCH_RESULT_VERSION!r}."))
        return errors

    @staticmethod
    def _check_manual_weights(context: PortfolioContext) -> list[PortfolioIssue]:
        warnings: list[PortfolioIssue] = []
        if context.configuration.allocation_method != AllocationMethod.MANUAL_WEIGHT:
            return warnings
        supplied_ids = {mw.strategy_id for mw in context.configuration.manual_weights}
        entry_ids = {e.strategy_model.metadata.id for e in context.entries}
        missing = entry_ids - supplied_ids
        if missing:
            warnings.append(
                PortfolioIssue(
                    path="configuration.manual_weights",
                    message=f"No manual weight supplied for {sorted(missing)}; falls back to equal weight if the whole set sums to 0.",
                    severity="warning",
                )
            )
        return warnings

    @staticmethod
    def _check_diversification(context: PortfolioContext) -> list[PortfolioIssue]:
        warnings: list[PortfolioIssue] = []
        if len(context.entries) < 2:
            warnings.append(PortfolioIssue(path="entries", message="Correlation, exposure, and diversification analytics are most meaningful with 2+ strategies.", severity="warning"))
        return warnings
