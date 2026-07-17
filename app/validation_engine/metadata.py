"""Static, self-describing identity for a completed validation run."""

from pydantic import BaseModel, ConfigDict, Field

VALIDATION_RESULT_VERSION = "1.0.0"


class ValidationMetadata(BaseModel):
    """Identity and versioning information carried onto a `ValidationResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    validation_id: str = Field(min_length=1, description="Unique id for this specific validation run.")
    strategy_id: str = Field(min_length=1, description="The source strategy id.")
    optimization_result_id: str = Field(min_length=1, description="The OptimizationResult this validation was run against.")
    optimization_checksum: str = Field(min_length=1, description="The consumed OptimizationResult's checksum.")
    candidate_id: str = Field(min_length=1, description="Which OptimizationCandidateOutcome was validated.")
    strategy_model_checksum: str = Field(min_length=1, description="The validated candidate's reconstructed StrategyModel checksum.")
    result_version: str = Field(default=VALIDATION_RESULT_VERSION, description="ValidationResult schema version.")
