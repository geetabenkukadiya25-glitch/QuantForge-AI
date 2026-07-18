"""Deterministic, keyword-based query intent classification.

`IntentClassifier` is a pure, rule-based lexical matcher -- NOT an LLM,
NOT a machine-learned classifier, and NOT connected to any external
service. Every rule is a simple, documented keyword/substring check
evaluated in a fixed priority order, so the same query always classifies
identically (see `test_determinism.py`).
"""

import re

from app.ai_assistant.models import IntentClassification, QueryIntent

# Canonical Smart Money Engine detector names this assistant recognizes by
# alias, so "show strategies using FVG" and "show strategies using fair
# value gap" both resolve to the same `detector_hint`. Mapped to the REAL
# names `app.smart_money_engine.SMCRegistry.register_builtins()` registers
# (e.g. "Break Of Structure", not "BOS") -- this is a lookup table, never
# a source of truth of its own.
DETECTOR_ALIASES: dict[str, str] = {
    "bos": "Break Of Structure",
    "break of structure": "Break Of Structure",
    "choch": "Change Of Character",
    "change of character": "Change Of Character",
    "fvg": "Fair Value Gap",
    "fair value gap": "Fair Value Gap",
    "order block": "Order Block",
    "liquidity pool": "Liquidity Pool",
    "liquidity sweep": "Liquidity Sweep",
    "liquidity": "Liquidity Pool",
    "mitigation": "Mitigation Block",
    "mitigation block": "Mitigation Block",
    "breaker": "Breaker Block",
    "breaker block": "Breaker Block",
    "premium": "Premium Zone",
    "discount": "Discount Zone",
}


def _contains_any(text: str, keywords: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(k for k in keywords if k in text)


def _detect_detector_hint(text: str) -> str | None:
    """Longest-alias-first match so 'fair value gap' isn't shadowed by a shorter substring."""
    for alias in sorted(DETECTOR_ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(alias) + r"\b", text):
            return DETECTOR_ALIASES[alias]
    return None


class IntentClassifier:
    """Classifies a raw natural-language query into one `QueryIntent`."""

    def classify(self, query: str) -> IntentClassification:
        text = query.strip().lower()

        compare_keywords = ("compare", " vs ", " versus ", " vs. ")
        if matched := _contains_any(text, compare_keywords):
            return IntentClassification(intent=QueryIntent.COMPARE_STRATEGIES, matched_keywords=matched)

        if "sharpe" in text and any(w in text for w in ("highest", "best", "top", "greatest")):
            return IntentClassification(intent=QueryIntent.HIGHEST_SHARPE_STRATEGY, matched_keywords=("sharpe",))

        if "drawdown" in text and "portfolio" in text and any(w in text for w in ("lowest", "least", "minimum", "smallest", "best")):
            return IntentClassification(intent=QueryIntent.LOWEST_DRAWDOWN_PORTFOLIO, matched_keywords=("drawdown", "portfolio"))

        detector_hint = _detect_detector_hint(text)
        if detector_hint and any(w in text for w in ("using", "with", "show", "find", "strategies", "strategy")):
            return IntentClassification(intent=QueryIntent.FIND_STRATEGIES_BY_DETECTOR, matched_keywords=("detector",), detector_hint=detector_hint)

        if "explain" in text or "what is" in text or "what does" in text:
            if "optimization" in text or "optimize" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_OPTIMIZATION, matched_keywords=("optimization",))
            if "validation" in text or "walk forward" in text or "monte carlo" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_VALIDATION, matched_keywords=("validation",))
            if "replay" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_REPLAY, matched_keywords=("replay",))
            if "portfolio" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_PORTFOLIO_ANALYTICS, matched_keywords=("portfolio",))
            if "extraction" in text or "ai extraction" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_AI_EXTRACTION, matched_keywords=("extraction",))
            if "indicator" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_INDICATOR, matched_keywords=("indicator",))
            if "detector" in text or detector_hint:
                return IntentClassification(intent=QueryIntent.EXPLAIN_DETECTOR, matched_keywords=("detector",), detector_hint=detector_hint)
            if "strategy" in text:
                return IntentClassification(intent=QueryIntent.EXPLAIN_STRATEGY, matched_keywords=("strategy",))

        return IntentClassification(intent=QueryIntent.GENERAL_SEARCH, matched_keywords=())
