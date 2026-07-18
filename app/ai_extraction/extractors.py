"""The domain-specific extraction stages: Indicator, Smart Money, Entry
Rule, Exit Rule, Risk Management, Session, Timeframe, and Parameter
Extractors.

Every extractor here is a pure, deterministic pattern/keyword matcher
over already-normalized document text. None of them interpret,
evaluate, or invent anything -- they only locate text that is already
present and classify it against a REAL, currently-registered vocabulary
(`app.indicator_engine`'s registered names, `app.smart_money_engine`'s
registered names, `app.context_engine.sessions`' real session names,
`app.data_engine.columns`' real timeframe labels) wherever a controlled
vocabulary exists, per the "single source of truth" discipline every
other engine in this platform follows.
"""

import re

from app.ai_extraction.models import (
    DetectorMention,
    IndicatorMention,
    ParameterMention,
    RiskMention,
    RuleMention,
    SessionMention,
    TimeframeMention,
)
from app.ai_extraction.sections import DetectedSection
from app.context_engine.sessions import SESSION_WINDOWS
from app.data_engine.columns import TIMEFRAME_TO_PANDAS_FREQ
from app.indicator_engine.registry import IndicatorRegistry
from app.smart_money_engine.registry import SMCRegistry

_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*(.+)$")


def _contains_name(text_lower: str, name_lower: str) -> bool:
    """Whole-word/whole-phrase match, not a raw substring check -- avoids
    false positives like "wma" matching inside "slowma" (which itself
    can only happen if upstream normalization corrupts "slow_ma"; this
    is still real defense-in-depth against any name that is a substring
    of another word)."""
    return re.search(r"\b" + re.escape(name_lower) + r"\b", text_lower) is not None


def _snippet(text: str, max_length: int) -> str:
    stripped = text.strip()
    return stripped if len(stripped) <= max_length else stripped[: max_length - 1] + "…"


def _bullet_lines(section: DetectedSection) -> list[tuple[int, str]]:
    """Every bullet/numbered line within a section, as (line offset, text)."""
    results = []
    for offset, line in enumerate(section.text.split("\n")):
        match = _BULLET_RE.match(line)
        if match:
            results.append((offset, match.group(1).strip()))
    return results


def _default_indicator_registry() -> IndicatorRegistry:
    registry = IndicatorRegistry()
    registry.register_builtins()
    return registry


def _default_smc_registry() -> SMCRegistry:
    registry = SMCRegistry()
    registry.register_builtins()
    return registry


class IndicatorExtractor:
    """Matches document text against real, registered Indicator Engine names."""

    def extract(self, lines: tuple[str, ...], registry: IndicatorRegistry | None, max_snippet: int) -> tuple[IndicatorMention, ...]:
        registry = registry or _default_indicator_registry()
        names = sorted((m.name for m in registry.list()), key=len, reverse=True)

        mentions: list[IndicatorMention] = []
        for line_no, line in enumerate(lines):
            lowered = line.lower()
            for name in names:
                if _contains_name(lowered, name.lower()):
                    mentions.append(IndicatorMention(matched_type=name, raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.9))
        return tuple(mentions)

    def unknown_items(self, sections: tuple[DetectedSection, ...], registry: IndicatorRegistry | None) -> tuple[str, ...]:
        """Bullet lines inside an "indicators" section that matched no registered name."""
        registry = registry or _default_indicator_registry()
        names_lower = [m.name.lower() for m in registry.list()]
        unknown = []
        for section in sections:
            if section.name != "indicators":
                continue
            for _, text in _bullet_lines(section):
                if not any(_contains_name(text.lower(), name) for name in names_lower):
                    unknown.append(text[:120])
        return tuple(dict.fromkeys(unknown))  # de-duplicated, order-preserving


class SmartMoneyExtractor:
    """Matches document text against real, registered Smart Money Engine names."""

    def extract(self, lines: tuple[str, ...], registry: SMCRegistry | None, max_snippet: int) -> tuple[DetectorMention, ...]:
        registry = registry or _default_smc_registry()
        names = sorted((m.name for m in registry.list()), key=len, reverse=True)

        mentions: list[DetectorMention] = []
        for line_no, line in enumerate(lines):
            lowered = line.lower()
            for name in names:
                if _contains_name(lowered, name.lower()):
                    mentions.append(DetectorMention(matched_type=name, raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.9))
        return tuple(mentions)

    def unknown_items(self, sections: tuple[DetectedSection, ...], registry: SMCRegistry | None) -> tuple[str, ...]:
        registry = registry or _default_smc_registry()
        names_lower = [m.name.lower() for m in registry.list()]
        unknown = []
        for section in sections:
            if section.name != "smart_money":
                continue
            for _, text in _bullet_lines(section):
                if not any(_contains_name(text.lower(), name) for name in names_lower):
                    unknown.append(text[:120])
        return tuple(dict.fromkeys(unknown))


_ENTRY_KEYWORDS = ("buy when", "enter long", "go long", "long entry", "buy entry", "enter short", "go short", "short entry", "sell entry", "buy signal", "sell signal")
_EXIT_KEYWORDS = ("exit when", "close position", "take profit", "close long", "close short", "exit long", "exit short", "sell to close", "buy to close", "exit signal")


class EntryRuleExtractor:
    """Candidate entry rules: bullet lines in an "entry" section (high confidence),
    or any line containing a strong entry keyword phrase (lower confidence)."""

    def extract(self, lines: tuple[str, ...], sections: tuple[DetectedSection, ...], max_snippet: int) -> tuple[RuleMention, ...]:
        return _extract_rule_mentions(lines, sections, section_name="entry", keywords=_ENTRY_KEYWORDS, max_snippet=max_snippet)


class ExitRuleExtractor:
    """Candidate exit rules: bullet lines in an "exit" section (high confidence),
    or any line containing a strong exit keyword phrase (lower confidence)."""

    def extract(self, lines: tuple[str, ...], sections: tuple[DetectedSection, ...], max_snippet: int) -> tuple[RuleMention, ...]:
        return _extract_rule_mentions(lines, sections, section_name="exit", keywords=_EXIT_KEYWORDS, max_snippet=max_snippet)


def _extract_rule_mentions(lines: tuple[str, ...], sections: tuple[DetectedSection, ...], section_name: str, keywords: tuple[str, ...], max_snippet: int) -> tuple[RuleMention, ...]:
    mentions: list[RuleMention] = []
    seen_lines: set[int] = set()

    for section in sections:
        if section.name != section_name:
            continue
        section_start = section.start_line + 1
        for offset, text in _bullet_lines(section):
            line_no = section_start + offset
            mentions.append(RuleMention(section=section_name, raw_text=_snippet(text, max_snippet), line_number=line_no, confidence=0.8))
            seen_lines.add(line_no)

    for line_no, line in enumerate(lines):
        if line_no in seen_lines:
            continue
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            mentions.append(RuleMention(section=section_name, raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.5))

    return tuple(mentions)


_RISK_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("stop_loss", re.compile(r"stop[- ]loss.{0,30}?(\d+(?:\.\d+)?)\s*(?:pips?|points?|%)", re.IGNORECASE)),
    ("take_profit", re.compile(r"take[- ]profit.{0,30}?(\d+(?:\.\d+)?)\s*(?:pips?|points?|%)", re.IGNORECASE)),
    ("risk_reward", re.compile(r"(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*(?:risk[- ]reward|r\s*:\s*r)?", re.IGNORECASE)),
    ("position_sizing", re.compile(r"risk\s+(\d+(?:\.\d+)?)\s*%\s*(?:per trade|of account|of equity)?", re.IGNORECASE)),
    ("max_drawdown", re.compile(r"max(?:imum)?\s+drawdown.{0,20}?(\d+(?:\.\d+)?)\s*%", re.IGNORECASE)),
)


class RiskManagementExtractor:
    """Regex-based detection of stop loss / take profit / risk-reward /
    position sizing / max drawdown statements."""

    def extract(self, lines: tuple[str, ...], max_snippet: int) -> tuple[RiskMention, ...]:
        mentions: list[RiskMention] = []
        for line_no, line in enumerate(lines):
            for category, pattern in _RISK_PATTERNS:
                match = pattern.search(line)
                if match:
                    value = None
                    try:
                        value = float(match.group(1))
                    except (IndexError, ValueError, TypeError):
                        pass
                    mentions.append(RiskMention(category=category, raw_text=_snippet(line, max_snippet), value=value, line_number=line_no, confidence=0.8 if value is not None else 0.5))
        return tuple(mentions)


class SessionExtractor:
    """Matches document text against real trading session names (`app.context_engine.sessions`)."""

    def extract(self, lines: tuple[str, ...], max_snippet: int) -> tuple[SessionMention, ...]:
        names = [w.name for w in SESSION_WINDOWS]
        mentions: list[SessionMention] = []
        for line_no, line in enumerate(lines):
            lowered = line.lower()
            for name in names:
                if _contains_name(lowered, name.lower()):
                    mentions.append(SessionMention(session_name=name, raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.9))
        return tuple(mentions)


_TIMEFRAME_ALIAS_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("M1", re.compile(r"\b1[- ]?min(?:ute)?s?\b", re.IGNORECASE)),
    ("M5", re.compile(r"\b5[- ]?min(?:ute)?s?\b", re.IGNORECASE)),
    ("M15", re.compile(r"\b15[- ]?min(?:ute)?s?\b", re.IGNORECASE)),
    ("M30", re.compile(r"\b30[- ]?min(?:ute)?s?\b", re.IGNORECASE)),
    ("H1", re.compile(r"\b1[- ]?hour(?:ly)?s?\b", re.IGNORECASE)),
    ("H4", re.compile(r"\b4[- ]?hour(?:ly)?s?\b", re.IGNORECASE)),
    ("D1", re.compile(r"\bdaily\b", re.IGNORECASE)),
    ("W1", re.compile(r"\bweekly\b", re.IGNORECASE)),
)


class TimeframeExtractor:
    """Matches document text against real timeframe labels (`app.data_engine.columns`),
    plus common plain-English aliases ("1 hour" -> H1, "daily" -> D1)."""

    def extract(self, lines: tuple[str, ...], max_snippet: int) -> tuple[TimeframeMention, ...]:
        codes = sorted(TIMEFRAME_TO_PANDAS_FREQ.keys(), key=len, reverse=True)
        code_pattern = re.compile(r"\b(" + "|".join(re.escape(c) for c in codes) + r")\b")

        mentions: list[TimeframeMention] = []
        for line_no, line in enumerate(lines):
            for match in code_pattern.finditer(line):
                mentions.append(TimeframeMention(timeframe=match.group(1).upper(), raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.9))
            for timeframe, pattern in _TIMEFRAME_ALIAS_PATTERNS:
                if pattern.search(line):
                    mentions.append(TimeframeMention(timeframe=timeframe, raw_text=_snippet(line, max_snippet), line_number=line_no, confidence=0.6))
        return tuple(mentions)


_PARAMETER_RE = re.compile(r"\(?\s*(\d{1,4})\s*\)?[- ]?(?:period|bar|candle)?s?\b")


class ParameterExtractor:
    """Best-guess numeric parameters near an already-detected indicator mention
    on the same line (e.g. "RSI(14)", "20-period SMA")."""

    def extract(self, indicator_mentions: tuple[IndicatorMention, ...], lines: tuple[str, ...], max_snippet: int) -> tuple[ParameterMention, ...]:
        mentions: list[ParameterMention] = []
        for indicator_mention in indicator_mentions:
            line = lines[indicator_mention.line_number] if indicator_mention.line_number < len(lines) else indicator_mention.raw_text
            match = _PARAMETER_RE.search(line)
            if match:
                mentions.append(
                    ParameterMention(
                        component_hint=indicator_mention.matched_type,
                        parameter_name="window",
                        value=float(match.group(1)),
                        raw_text=_snippet(line, max_snippet),
                        line_number=indicator_mention.line_number,
                        confidence=0.6,
                    )
                )
        return tuple(mentions)
