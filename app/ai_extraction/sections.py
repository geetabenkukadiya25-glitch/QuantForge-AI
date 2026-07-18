"""Section Detection: heuristically splits a parsed document into named
sections (e.g. "Entry Rules", "Risk Management") so downstream extractors
can prioritize matches found within a relevantly-named section.

Detection is purely structural/lexical (markdown headings, ALL-CAPS short
lines, "Label:" lines matching a known keyword) -- never a judgment about
what the section's CONTENT means.
"""

import re

from app.ai_extraction.models import DetectedSection
from app.ai_extraction.parser import ParsedDocument

_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$")
_LABEL_LINE_RE = re.compile(r"^([A-Za-z][A-Za-z /]{2,40}):\s*$")
_ALL_CAPS_RE = re.compile(r"^[A-Z][A-Z /]{2,40}$")

# Canonical section name -> keywords that identify a heading as that section.
SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "indicators": ("indicator", "indicators"),
    "smart_money": ("smart money", "smc", "market structure", "order block", "liquidity", "ict"),
    "entry": ("entry", "entry rules", "buy rules", "long entry", "short entry", "entries"),
    "exit": ("exit", "exit rules", "take profit rules", "close rules", "exits"),
    "risk": ("risk", "risk management", "money management", "position sizing"),
    "session": ("session", "sessions", "trading session", "trading sessions"),
    "timeframe": ("timeframe", "time frame", "chart timeframe", "timeframes"),
    "parameters": ("parameter", "parameters", "settings", "inputs"),
}


def _canonical_name(heading_text: str) -> str:
    lowered = heading_text.strip().lower()
    for canonical, keywords in SECTION_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return canonical
    return lowered


class SectionDetector:
    """Detects heading-delimited sections within a `ParsedDocument`."""

    def detect(self, document: ParsedDocument) -> tuple[DetectedSection, ...]:
        headings: list[tuple[int, str]] = []  # (line_index, canonical_name)

        for index, line in enumerate(document.lines):
            stripped = line.strip()
            if not stripped:
                continue

            match = _MARKDOWN_HEADING_RE.match(stripped)
            if match:
                headings.append((index, _canonical_name(match.group(1))))
                continue

            match = _LABEL_LINE_RE.match(stripped)
            if match:
                headings.append((index, _canonical_name(match.group(1))))
                continue

            if _ALL_CAPS_RE.match(stripped) and len(stripped.split()) <= 6:
                headings.append((index, _canonical_name(stripped)))

        if not headings:
            return ()

        sections: list[DetectedSection] = []
        for position, (start_line, name) in enumerate(headings):
            end_line = headings[position + 1][0] - 1 if position + 1 < len(headings) else len(document.lines) - 1
            body_start = start_line + 1
            text = "\n".join(document.lines[body_start : end_line + 1]).strip()
            sections.append(DetectedSection(name=name, start_line=start_line, end_line=max(end_line, start_line), text=text))

        return tuple(sections)
