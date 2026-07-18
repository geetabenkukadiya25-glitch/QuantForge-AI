"""Tests for `PortfolioReport`."""

import pandas as pd

from app.portfolio_engine.report import PortfolioReport
from app.portfolio_engine.runner import PortfolioRunner


def _report(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    return PortfolioReport(result)


def test_executive_summary_is_dict(portfolio_context):
    report = _report(portfolio_context)
    summary = report.executive_summary()
    assert isinstance(summary, dict)
    assert summary["total_strategies"] == 2


def test_portfolio_report_is_dict(portfolio_context):
    report = _report(portfolio_context)
    assert isinstance(report.portfolio_report(), dict)


def test_risk_report_has_expected_keys(portfolio_context):
    report = _report(portfolio_context)
    risk = report.risk_report()
    assert "portfolio_max_drawdown_pct" in risk
    assert "risk_score" in risk
    assert "risk_allocation" in risk
    assert len(risk["risk_allocation"]) == 2


def test_allocation_table_has_one_row_per_strategy(portfolio_context):
    report = _report(portfolio_context)
    table = report.allocation_table()
    assert isinstance(table, pd.DataFrame)
    assert len(table) == 2


def test_symbol_allocation_table(portfolio_context):
    report = _report(portfolio_context)
    table = report.symbol_allocation_table()
    assert isinstance(table, pd.DataFrame)


def test_sector_allocation_table_is_empty(portfolio_context):
    report = _report(portfolio_context)
    table = report.sector_allocation_table()
    assert table.empty


def test_correlation_table_has_one_row_for_two_strategies(portfolio_context):
    report = _report(portfolio_context)
    table = report.correlation_table()
    assert len(table) == 1


def test_exposure_table(portfolio_context):
    report = _report(portfolio_context)
    table = report.exposure_table()
    assert isinstance(table, pd.DataFrame)
    assert "symbol" in table.columns


def test_ranking_table_has_category_column(portfolio_context):
    report = _report(portfolio_context)
    table = report.ranking_table()
    assert "category" in table.columns
    assert len(table) >= 4  # best/worst/highest-risk/lowest-risk at minimum


def test_analytics_report_is_dict(portfolio_context):
    report = _report(portfolio_context)
    analytics = report.analytics_report()
    assert isinstance(analytics, dict)
    assert "portfolio_quality_score" in analytics


def test_result_property_returns_underlying_result(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    report = PortfolioReport(result)
    assert report.result is result
