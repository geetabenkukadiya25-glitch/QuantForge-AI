"""Static, self-describing identity for a completed portfolio build."""

from pydantic import BaseModel, ConfigDict, Field

PORTFOLIO_RESULT_VERSION = "1.0.0"


class PortfolioMetadata(BaseModel):
    """Identity and versioning information carried onto a `PortfolioResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    portfolio_id: str = Field(min_length=1, description="Unique id for this specific portfolio build.")
    strategy_ids: tuple[str, ...] = Field(min_length=1, description="Every strategy id combined into this portfolio.")
    strategy_checksums: tuple[str, ...] = Field(description="The consumed StrategyModels' checksums, same order as strategy_ids.")
    backtest_result_ids: tuple[str, ...] = Field(description="The consumed BacktestResults' ids, same order as strategy_ids.")
    result_version: str = Field(default=PORTFOLIO_RESULT_VERSION, description="PortfolioResult schema version.")
