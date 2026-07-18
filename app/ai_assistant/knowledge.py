"""Static, documentation-sourced explanations plus Knowledge Base lookups.

`ENGINE_GLOSSARY` is a small, fixed dictionary of one-paragraph
explanations for each platform engine, paraphrased directly from this
project's own `docs/ARCHITECTURE.md` -- never generated, never fetched
externally. It is the deterministic source for "Explain optimization" /
"Explain validation" / "Explain replay" / "Explain portfolio analytics" /
"Explain AI extraction" style questions, which ask about the PLATFORM
itself rather than about a specific stored result.

`KnowledgeLookup` additionally searches any attached `KnowledgeRegistry`'s
already-built `KnowledgeResult`s for authored entries matching a keyword
-- real, human-authored content, never generated here.
"""

from app.ai_assistant.models import SearchResultItem, SearchSourceType
from app.knowledge_base.registry import KnowledgeRegistry

ENGINE_GLOSSARY: dict[str, str] = {
    "optimization": (
        "The Optimization Engine (app/optimization_engine/) searches a StrategyModel's "
        "parameter space (Grid Search or Random Search) using the existing, unmodified "
        "Backtesting Engine to evaluate each candidate. It never re-implements simulation "
        "logic of its own -- every candidate's statistics come from a real BacktestResult."
    ),
    "validation": (
        "The Walk Forward & Monte Carlo Validation Engine (app/validation_engine/) validates "
        "an already-chosen Optimization Engine candidate: walk-forward windowing (in-sample / "
        "out-of-sample splits) and Monte Carlo resampling of its already-produced trade list. "
        "It never searches for a better candidate and never simulates a new trade itself -- "
        "every statistic comes from PerformanceStatistics or resampling an already-produced "
        "trade list. It produces a RobustnessScore, ConfidenceScore, and StabilityScore."
    ),
    "replay": (
        "The Professional Replay Engine (app/replay_engine/) plays back historical data "
        "candle-by-candle (Timeline, Cursor, Player, Controller) and MAY overlay an "
        "already-built strategy's indicators/detections and an already-run backtest's trade "
        "lifecycle, purely for visualization. It never trades, never re-runs a backtest, and "
        "never connects to a broker or MT5."
    ),
    "portfolio": (
        "The Professional Portfolio Management Engine (app/portfolio_engine/) combines "
        "multiple already-completed strategies into a single portfolio: allocation (Equal "
        "Weight, Risk Parity, Volatility Weight, Sharpe Weight, Manual Weight), correlation, "
        "exposure, ranking, and portfolio-quality analytics (diversification, correlation, "
        "concentration, risk, and a composite quality score). It never trades, never "
        "connects to a broker or MT5, never optimizes, and never validates -- only "
        "aggregation over already-completed Strategy Builder/Backtesting outputs."
    ),
    "extraction": (
        "The AI Strategy Extraction Engine (app/ai_extraction/) converts already-obtained "
        "external strategy document text (YouTube transcript, PDF, Markdown, plain text, "
        "Pine Script, MQL4/5, EasyLanguage, pseudocode, OCR text) into a draft SDL document, "
        "a confidence report, and a missing-information report. It is a deterministic, "
        "offline, pattern/keyword-matching pipeline -- NOT a generative AI model, and it "
        "NEVER calls an external API. Every output is an explicit DRAFT requiring human "
        "review before use."
    ),
    "strategy": (
        "A strategy in QuantForge AI starts as an SDL (Strategy Definition Language) "
        "document, then Strategy Builder (app/strategy_builder/) resolves it against the "
        "Indicator Engine and Smart Money Engine into an executable StrategyModel -- the "
        "single artifact every downstream engine (Backtesting, Optimization, Validation, "
        "Replay, Research, Portfolio) consumes without ever re-parsing the raw document."
    ),
    "indicator": (
        "The Indicator Engine (app/indicator_engine/) computes technical indicators "
        "(calculation only -- no signals, no decisions) over already-loaded historical "
        "data. Each indicator declares its own IndicatorMetadata: name, category, required "
        "inputs, produced outputs, and tunable parameters."
    ),
    "detector": (
        "The Smart Money Engine (app/smart_money_engine/) detects Smart Money Concepts "
        "(BOS, CHoCH, FVG, Order Blocks, Liquidity, Mitigation, Breaker, Premium/Discount, "
        "and more) over already-loaded historical data (detection only -- no signals, no "
        "decisions). Each detector declares its own SMCMetadata: name, category, required "
        "inputs, produced outputs, and tunable parameters."
    ),
    "knowledge_base": (
        "The Knowledge Base Platform (app/knowledge_base/) is an institutional documentation "
        "and trading-knowledge system -- authored, static reference content across SMC, ICT, "
        "price action, indicators, patterns, risk management, and more. It never trades, "
        "optimizes, backtests, validates, or replays."
    ),
    "research": (
        "The Research & Strategy Intelligence Engine (app/research_engine/) compares and "
        "ranks multiple already-backtested strategies: statistics, scoring "
        "(StrategyScore/ConfidenceScore/InstitutionalQualityScore), advanced analytics, "
        "insights, and recommendations. It consumes ONLY already-completed outputs and "
        "never re-runs a backtest, optimization, or validation itself."
    ),
}


def _enabled_results(registry: KnowledgeRegistry) -> list:
    """Every enabled, registered `KnowledgeResult` body.

    `KnowledgeRegistry.list()` returns only `KnowledgeMetadata` (no
    entries), and `KnowledgeMetadata.knowledge_id` is a DIFFERENT id than
    the internal `result_id` key `.load()` actually needs -- there is no
    public way to go from a `list()`-returned metadata object back to its
    full result body. Reading the registry's internal `_results` mapping
    (never mutating it) is the only way to search full result bodies
    without modifying `KnowledgeRegistry` itself, which is out of scope
    for this phase.
    """
    enabled_ids = {m.knowledge_id for m in registry.list(include_disabled=False)}
    return [r for r in registry._results.values() if r.metadata.knowledge_id in enabled_ids]  # noqa: SLF001


class KnowledgeLookup:
    """Deterministic lookups over the static glossary and any attached `KnowledgeRegistry`."""

    def explain(self, topic: str) -> str | None:
        """Return the fixed glossary paragraph for `topic`, or None if unknown."""
        return ENGINE_GLOSSARY.get(topic.strip().lower())

    def search_entries(self, registry: KnowledgeRegistry | None, keyword: str) -> tuple[SearchResultItem, ...]:
        """Search every enabled, registered `KnowledgeResult`'s entries for `keyword`."""
        if registry is None or not keyword:
            return ()
        needle = keyword.strip().lower()
        items: list[SearchResultItem] = []
        for result in _enabled_results(registry):
            for entry in result.entries:
                haystack = f"{entry.title} {entry.summary} {entry.content}".lower()
                if needle in haystack:
                    items.append(
                        SearchResultItem(
                            source_type=SearchSourceType.KNOWLEDGE_BASE,
                            item_id=entry.entry_id,
                            title=entry.title,
                            snippet=entry.summary,
                            tags=entry.tags,
                        )
                    )
        return tuple(sorted(items, key=lambda i: i.item_id))
