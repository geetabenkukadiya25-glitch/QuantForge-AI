"""`DocumentParser`/`SectionDetector`: text structuring and heading detection."""

from app.ai_extraction.parser import DocumentParser
from app.ai_extraction.sections import SectionDetector
from tests.ai_extraction.conftest import SAMPLE_MARKDOWN


def test_parser_splits_lines_and_paragraphs() -> None:
    parsed = DocumentParser().parse("line one\nline two\n\nsecond paragraph")
    assert parsed.lines == ("line one", "line two", "", "second paragraph")
    assert parsed.paragraphs == ("line one\nline two", "second paragraph")


def test_parser_handles_empty_text() -> None:
    parsed = DocumentParser().parse("")
    assert parsed.lines == ("",)
    assert parsed.paragraphs == ()


def test_section_detector_finds_markdown_headings() -> None:
    parsed = DocumentParser().parse(SAMPLE_MARKDOWN)
    sections = SectionDetector().detect(parsed)
    names = {s.name for s in sections}
    assert "entry" in names
    assert "exit" in names
    assert "risk" in names
    assert "indicators" in names
    assert "timeframe" in names


def test_section_text_contains_only_its_own_body() -> None:
    parsed = DocumentParser().parse(SAMPLE_MARKDOWN)
    sections = SectionDetector().detect(parsed)
    entry_section = next(s for s in sections if s.name == "entry")
    assert "fast_ma crosses above slow_ma" in entry_section.text
    assert "Take profit" not in entry_section.text


def test_no_headings_returns_empty_sections() -> None:
    parsed = DocumentParser().parse("Just a single line of prose with no headings at all.")
    assert SectionDetector().detect(parsed) == ()


def test_all_caps_short_line_detected_as_heading() -> None:
    parsed = DocumentParser().parse("RISK MANAGEMENT\nRisk 1% per trade.")
    sections = SectionDetector().detect(parsed)
    assert any(s.name == "risk" for s in sections)


def test_label_colon_line_detected_as_heading() -> None:
    parsed = DocumentParser().parse("Entry Rules:\nBuy when RSI crosses above 30.")
    sections = SectionDetector().detect(parsed)
    assert any(s.name == "entry" for s in sections)
