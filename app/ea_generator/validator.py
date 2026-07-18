"""Pre-execution validation for an `EAGeneratorContext`.

Covers: the strategy has something to generate (a non-empty execution
pipeline), the output filename is a safe, plain `.mq5` basename, and
version compatibility plus identity consistency of every consumed
artifact (`StrategyModel`, and -- if present -- `ValidationResult`,
`OptimizationResult`, `ResearchResult`, `PortfolioResult`).
"""

from dataclasses import dataclass, field

from app.ea_generator.context import EAGeneratorContext
from app.optimization_engine.metadata import OPTIMIZATION_RESULT_VERSION
from app.research_engine.metadata import RESEARCH_RESULT_VERSION
from app.portfolio_engine.metadata import PORTFOLIO_RESULT_VERSION
from app.strategy_builder.metadata import STRATEGY_MODEL_VERSION
from app.utils.logger import get_logger
from app.validation_engine.metadata import VALIDATION_RESULT_VERSION

logger = get_logger(__name__)

_INVALID_FILENAME_CHARS = set('/\\:*?"<>|')


@dataclass
class EAGeneratorIssue:
    """A single validation finding, anchored to a path within the EA generation context."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.path}: {self.message}"


@dataclass
class EAGeneratorCheckResult:
    """Outcome of running `EAGeneratorValidator.validate`.

    Named `EAGeneratorCheckResult`, not `EAGeneratorResult` -- that name
    is reserved for this module's root artifact, the same
    disambiguation precedent `PortfolioCheckResult`/`AssistantCheckResult`
    established.
    """

    errors: list[EAGeneratorIssue] = field(default_factory=list)
    warnings: list[EAGeneratorIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def report(self) -> str:
        lines = [f"Validation {'PASSED' if self.is_valid else 'FAILED'}"]
        lines += [str(issue) for issue in self.errors]
        lines += [str(issue) for issue in self.warnings]
        return "\n".join(lines)


class EAGeneratorValidator:
    """Validates an `EAGeneratorContext` before any code generation happens."""

    def validate(self, context: EAGeneratorContext) -> EAGeneratorCheckResult:
        """Validate `context`. Never raises -- inspect `.is_valid`."""
        errors: list[EAGeneratorIssue] = []
        warnings: list[EAGeneratorIssue] = []

        errors += self._check_strategy_has_content(context)
        errors += self._check_output_filename(context)
        errors += self._check_versions(context)
        errors += self._check_identity_consistency(context)
        warnings += self._check_risk_defaults(context)

        result = EAGeneratorCheckResult(errors=errors, warnings=warnings)
        logger.info("Validated EA generation context for strategy %r: %d error(s), %d warning(s)", context.strategy_model.metadata.id, len(errors), len(warnings))
        return result

    @staticmethod
    def _check_strategy_has_content(context: EAGeneratorContext) -> list[EAGeneratorIssue]:
        model = context.strategy_model
        if not model.execution_pipeline.steps:
            return [EAGeneratorIssue(path="strategy_model.execution_pipeline", message="Strategy has an empty execution pipeline; nothing to generate.")]
        return []

    @staticmethod
    def _check_output_filename(context: EAGeneratorContext) -> list[EAGeneratorIssue]:
        errors: list[EAGeneratorIssue] = []
        filename = context.configuration.output_filename
        if any(char in _INVALID_FILENAME_CHARS for char in filename):
            errors.append(EAGeneratorIssue(path="configuration.output_filename", message=f"{filename!r} must be a plain filename with no path separators or reserved characters."))
        if ".." in filename:
            errors.append(EAGeneratorIssue(path="configuration.output_filename", message=f"{filename!r} must not contain '..'."))
        if not filename.lower().endswith(".mq5"):
            errors.append(EAGeneratorIssue(path="configuration.output_filename", message=f"{filename!r} must end with '.mq5'."))
        return errors

    @staticmethod
    def _check_versions(context: EAGeneratorContext) -> list[EAGeneratorIssue]:
        errors: list[EAGeneratorIssue] = []
        strategy_id = context.strategy_model.metadata.id

        model_version = context.strategy_model.metadata.model_version
        if model_version != STRATEGY_MODEL_VERSION:
            errors.append(EAGeneratorIssue(path="strategy_model", message=f"Unsupported StrategyModel version {model_version!r}. Expected {STRATEGY_MODEL_VERSION!r}."))

        if context.validation_result is not None:
            version = context.validation_result.metadata.result_version
            if version != VALIDATION_RESULT_VERSION:
                errors.append(EAGeneratorIssue(path=f"entries[{strategy_id}].validation_result", message=f"Unsupported ValidationResult version {version!r}. Expected {VALIDATION_RESULT_VERSION!r}."))

        if context.optimization_result is not None:
            version = context.optimization_result.metadata.result_version
            if version != OPTIMIZATION_RESULT_VERSION:
                errors.append(EAGeneratorIssue(path=f"entries[{strategy_id}].optimization_result", message=f"Unsupported OptimizationResult version {version!r}. Expected {OPTIMIZATION_RESULT_VERSION!r}."))

        if context.research_result is not None:
            version = context.research_result.metadata.result_version
            if version != RESEARCH_RESULT_VERSION:
                errors.append(EAGeneratorIssue(path=f"entries[{strategy_id}].research_result", message=f"Unsupported ResearchResult version {version!r}. Expected {RESEARCH_RESULT_VERSION!r}."))

        if context.portfolio_result is not None:
            version = context.portfolio_result.metadata.result_version
            if version != PORTFOLIO_RESULT_VERSION:
                errors.append(EAGeneratorIssue(path=f"entries[{strategy_id}].portfolio_result", message=f"Unsupported PortfolioResult version {version!r}. Expected {PORTFOLIO_RESULT_VERSION!r}."))

        return errors

    @staticmethod
    def _check_identity_consistency(context: EAGeneratorContext) -> list[EAGeneratorIssue]:
        errors: list[EAGeneratorIssue] = []
        strategy_id = context.strategy_model.metadata.id

        if context.validation_result is not None and context.validation_result.metadata.strategy_id != strategy_id:
            errors.append(
                EAGeneratorIssue(
                    path="validation_result",
                    message=f"ValidationResult.metadata.strategy_id {context.validation_result.metadata.strategy_id!r} does not match StrategyModel {strategy_id!r}.",
                )
            )

        if context.optimization_result is not None and context.optimization_result.metadata.strategy_id != strategy_id:
            errors.append(
                EAGeneratorIssue(
                    path="optimization_result",
                    message=f"OptimizationResult.metadata.strategy_id {context.optimization_result.metadata.strategy_id!r} does not match StrategyModel {strategy_id!r}.",
                )
            )

        if context.research_result is not None and strategy_id not in context.research_result.metadata.strategy_ids:
            errors.append(EAGeneratorIssue(path="research_result", message=f"ResearchResult does not include strategy {strategy_id!r} among its analyzed strategies."))

        if context.portfolio_result is not None and strategy_id not in context.portfolio_result.metadata.strategy_ids:
            errors.append(EAGeneratorIssue(path="portfolio_result", message=f"PortfolioResult does not include strategy {strategy_id!r} among its member strategies."))

        return errors

    @staticmethod
    def _check_risk_defaults(context: EAGeneratorContext) -> list[EAGeneratorIssue]:
        warnings: list[EAGeneratorIssue] = []
        cfg = context.configuration
        if cfg.stop_loss_points == 0 and cfg.take_profit_points == 0:
            warnings.append(EAGeneratorIssue(path="configuration", message="Both stop_loss_points and take_profit_points are 0; the generated skeleton has no risk exit configured.", severity="warning"))
        return warnings
