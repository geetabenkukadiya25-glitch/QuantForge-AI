"""Static, self-describing identity for a built strategy.

Derived from the source `StrategyDefinition.metadata` (SDL), plus this
module's own schema version -- `StrategyModel` is versioned along three
independent axes, mirroring the SDL/Context Engine pattern: the SDL
schema version, the strategy's own revision, and this module's model
schema version.
"""

from pydantic import BaseModel, ConfigDict, Field

STRATEGY_MODEL_VERSION = "1.0.0"


class StrategyMetadata(BaseModel):
    """Identity and versioning information carried onto a built `StrategyModel`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(min_length=1, description="The source SDL strategy id.")
    name: str = Field(min_length=1)
    description: str | None = None
    category: str | None = None
    sdl_version: str = Field(description="SDL schema version of the source document.")
    strategy_version: str = Field(description="Revision of the source strategy document.")
    model_version: str = Field(default=STRATEGY_MODEL_VERSION, description="StrategyModel schema version.")
