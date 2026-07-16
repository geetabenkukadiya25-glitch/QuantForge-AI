"""
Future database schema documentation.

This module intentionally contains no executable table definitions yet.
It documents the tables later phases will introduce so the eventual
schema additions stay consistent with the pipeline defined in the project
mission (idea -> strategy -> backtest -> optimization -> analytics ->
walk-forward -> Monte Carlo -> risk -> EA generation).

Each entry will become a real table (via `DatabaseManager`) once its
owning phase is implemented -- do not add SQL here during Phase 1.
"""

FUTURE_TABLES: dict[str, str] = {
    "strategies": "AI-generated and user-defined strategy definitions.",
    "backtests": "Backtest run records and summary performance metrics.",
    "optimization_runs": "Parameter optimization sweeps and their results.",
    "walk_forward_results": "Walk-forward validation windows and outcomes.",
    "monte_carlo_results": "Monte Carlo simulation runs and risk distributions.",
    "generated_eas": "MetaTrader 5 Expert Advisors generated from strategies.",
}
