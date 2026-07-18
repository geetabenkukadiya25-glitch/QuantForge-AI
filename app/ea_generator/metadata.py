"""Static, self-describing identity for a completed EA generation run."""

from pydantic import BaseModel, ConfigDict, Field

EA_RESULT_VERSION = "1.0.0"


class EAGeneratorMetadata(BaseModel):
    """Identity and versioning information carried onto an `EAGeneratorResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    ea_id: str = Field(min_length=1, description="Unique id for this specific EA generation run.")
    strategy_id: str = Field(min_length=1, description="The source StrategyModel's strategy id.")
    strategy_checksum: str = Field(min_length=1, description="The consumed StrategyModel's checksum.")
    output_filename: str = Field(min_length=1, description="The requested .mq5 output filename.")
    result_version: str = Field(default=EA_RESULT_VERSION, description="EAGeneratorResult schema version.")
