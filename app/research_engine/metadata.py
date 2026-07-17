"""Static, self-describing identity for a completed research run."""

from pydantic import BaseModel, ConfigDict, Field

RESEARCH_RESULT_VERSION = "1.0.0"


class ResearchMetadata(BaseModel):
    """Identity and versioning information carried onto a `ResearchResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    research_id: str = Field(min_length=1, description="Unique id for this specific research run.")
    strategy_ids: tuple[str, ...] = Field(min_length=1, description="Every strategy id analyzed by this run.")
    strategy_checksums: tuple[str, ...] = Field(description="The consumed StrategyModels' checksums, same order as strategy_ids.")
    backtest_result_ids: tuple[str, ...] = Field(description="The consumed BacktestResults' ids, same order as strategy_ids.")
    result_version: str = Field(default=RESEARCH_RESULT_VERSION, description="ResearchResult schema version.")
