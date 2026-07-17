"""Static, self-describing identity for a completed backtest run.

`BacktestResult` is versioned along three independent axes, mirroring the
`StrategyModel`/`ContextSnapshot` pattern: the source `StrategyModel`'s own
version, the id of the specific strategy build consumed, and this module's
own result-schema version.
"""

from pydantic import BaseModel, ConfigDict, Field

BACKTEST_RESULT_VERSION = "1.0.0"


class BacktestMetadata(BaseModel):
    """Identity and versioning information carried onto a `BacktestResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    backtest_id: str = Field(min_length=1, description="Unique id for this specific backtest run.")
    strategy_id: str = Field(min_length=1, description="The source SDL strategy id.")
    strategy_model_id: str = Field(min_length=1, description="The specific StrategyModel build consumed.")
    strategy_checksum: str = Field(min_length=1, description="The consumed StrategyModel's checksum.")
    strategy_model_version: str = Field(description="StrategyModel schema version of the source build.")
    result_version: str = Field(default=BACKTEST_RESULT_VERSION, description="BacktestResult schema version.")
