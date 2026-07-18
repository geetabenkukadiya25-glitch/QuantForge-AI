"""Document Parser: splits normalized text into addressable lines/paragraphs.

Pure text structuring -- no interpretation of meaning happens here; that
is every downstream extractor's job.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedDocument:
    """Line- and paragraph-addressable view over one normalized document."""

    lines: tuple[str, ...]
    paragraphs: tuple[str, ...]


class DocumentParser:
    """Splits `DocumentContent.normalized_text` into lines and paragraphs."""

    def parse(self, normalized_text: str) -> ParsedDocument:
        lines = tuple(normalized_text.split("\n"))
        paragraphs = tuple(p.strip() for p in normalized_text.split("\n\n") if p.strip())
        return ParsedDocument(lines=lines, paragraphs=paragraphs)
