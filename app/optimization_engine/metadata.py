"""Static, self-describing identity for a completed optimization run."""

from pydantic import BaseModel, ConfigDict, Field

OPTIMIZATION_RESULT_VERSION = "1.0.0"


class OptimizationMetadata(BaseModel):
    """Identity and versioning information carried onto an `OptimizationResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    optimization_id: str = Field(min_length=1, description="Unique id for this specific optimization run.")
    strategy_id: str = Field(min_length=1, description="The source strategy id (StrategyModel.metadata.id).")
    base_strategy_model_id: str = Field(min_length=1, description="The base StrategyModel build every candidate was derived from.")
    base_strategy_checksum: str = Field(min_length=1, description="The base StrategyModel's checksum.")
    strategy_model_version: str = Field(description="StrategyModel schema version of the base build.")
    result_version: str = Field(default=OPTIMIZATION_RESULT_VERSION, description="OptimizationResult schema version.")
