"""Strategy Analyzer: derives a best-guess strategy name and description
from the document's own text -- never invents one. If nothing usable is
found, both fall back to explicit placeholders that `MissingInformationDetector`
flags for human review, rather than a fabricated-sounding default.
"""

from dataclasses import dataclass

from app.ai_extraction.parser import ParsedDocument

DEFAULT_NAME = "Untitled Extracted Strategy"


@dataclass(frozen=True)
class StrategyOverview:
    name: str
    description: str
    name_detected: bool
    description_detected: bool


class StrategyAnalyzer:
    """Derives `(name, description)` from the first heading/title-like line
    and the first substantial paragraph -- both taken verbatim from the
    source text, never generated."""

    def analyze(self, document: ParsedDocument) -> StrategyOverview:
        name, name_detected = self._first_title_line(document)
        description, description_detected = self._first_paragraph(document, exclude=name if name_detected else None)
        return StrategyOverview(name=name, description=description, name_detected=name_detected, description_detected=description_detected)

    @staticmethod
    def _first_title_line(document: ParsedDocument) -> tuple[str, bool]:
        for line in document.lines:
            stripped = line.strip().lstrip("#").strip()
            if stripped:
                return stripped[:120], True
        return DEFAULT_NAME, False

    @staticmethod
    def _first_paragraph(document: ParsedDocument, exclude: str | None) -> tuple[str, bool]:
        for paragraph in document.paragraphs:
            candidate = paragraph.strip()
            # Normalized the same way `_first_title_line` derives `name` --
            # otherwise a paragraph consisting solely of the title heading
            # (still carrying its raw '#' markers) wouldn't match `exclude`
            # and would be mistaken for the description.
            normalized = candidate.lstrip("#").strip()
            if candidate and normalized != (exclude or ""):
                return candidate[:500], True
        return "", False
