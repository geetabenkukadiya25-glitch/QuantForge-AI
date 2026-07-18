"""Tests for `PortfolioCompiler`."""

from app.portfolio_engine.compiler import PortfolioCompiler
from app.portfolio_engine.runner import PortfolioRunner


def test_compile_produces_valid_checksum(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    assert len(result.checksum) == 64  # sha256 hex digest length
    assert all(c in "0123456789abcdef" for c in result.checksum)


def test_compile_is_deterministic_for_same_context(portfolio_context):
    result_1 = PortfolioRunner().execute(portfolio_context)
    result_2 = PortfolioRunner().execute(portfolio_context)
    assert result_1.checksum == result_2.checksum


def test_compile_strategy_ids_are_sorted(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    assert result.metadata.strategy_ids == tuple(sorted(result.metadata.strategy_ids))


def test_compile_checksum_excludes_identity_fields(portfolio_context):
    result_1 = PortfolioRunner().execute(portfolio_context)
    result_2 = PortfolioRunner().execute(portfolio_context)
    assert result_1.result_id != result_2.result_id
    assert result_1.metadata.portfolio_id != result_2.metadata.portfolio_id
    assert result_1.checksum == result_2.checksum


def test_compile_metadata_lengths_match_entry_count(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    assert len(result.metadata.strategy_ids) == 2
    assert len(result.metadata.strategy_checksums) == 2
    assert len(result.metadata.backtest_result_ids) == 2


def test_compiler_can_be_used_directly(portfolio_context):
    from app.portfolio_engine.allocation import AllocationEngine
    from app.portfolio_engine.analytics import AnalyticsEngine
    from app.portfolio_engine.correlation import CorrelationEngine
    from app.portfolio_engine.ranking import RankingEngine
    from app.portfolio_engine.risk import RiskEngine
    from app.portfolio_engine.statistics import PortfolioStatisticsEngine

    entries = portfolio_context.entries
    weights = AllocationEngine().resolve_weights(entries, portfolio_context.configuration)
    risk_contribution = RiskEngine().risk_contribution_pct(entries, weights)
    allocation = AllocationEngine().allocate(entries, portfolio_context.configuration, risk_contribution)
    drawdown = RiskEngine().portfolio_max_drawdown_pct(entries, weights)
    statistics = PortfolioStatisticsEngine().compute(entries, weights, drawdown)
    correlation_matrix = CorrelationEngine().correlate(entries)
    exposure = CorrelationEngine().exposure(entries, weights)
    ranking = RankingEngine().rank(entries)
    risk_score = RiskEngine().risk_score(drawdown, correlation_matrix.average_correlation)
    analytics = AnalyticsEngine().analyze(entries, weights, correlation_matrix, statistics, risk_score)

    from app.portfolio_engine.models import PortfolioExecutiveSummary

    summary = PortfolioExecutiveSummary(total_strategies=statistics.total_strategies, total_net_profit=statistics.total_net_profit, portfolio_quality_score=analytics.portfolio_quality_score)

    result = PortfolioCompiler().compile(portfolio_context, allocation, statistics, correlation_matrix, exposure, ranking, analytics, summary)
    assert result.result_id
    assert result.checksum
