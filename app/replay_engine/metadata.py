"""Static, self-describing identity for a completed replay preparation."""

from pydantic import BaseModel, ConfigDict, Field

REPLAY_RESULT_VERSION = "1.0.0"


class ReplayMetadata(BaseModel):
    """Identity and versioning information carried onto a `ReplayResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    replay_id: str = Field(min_length=1, description="Unique id for this specific replay preparation.")
    data_checksum: str = Field(min_length=1, description="Content hash of the consumed historical data slice.")
    strategy_id: str | None = Field(default=None, description="The source strategy id, if a StrategyModel was supplied (visualization only).")
    strategy_model_id: str | None = Field(default=None, description="The specific StrategyModel build consumed, if any.")
    strategy_checksum: str | None = Field(default=None, description="The consumed StrategyModel's checksum, if any.")
    backtest_result_id: str | None = Field(default=None, description="The BacktestResult consumed for trade-lifecycle visualization, if any.")
    backtest_checksum: str | None = Field(default=None, description="The consumed BacktestResult's checksum, if any.")
    result_version: str = Field(default=REPLAY_RESULT_VERSION, description="ReplayResult schema version.")
