"""`StrategyAnalyzer`: derives name/description from the document's own text."""

from app.ai_extraction.analyzer import DEFAULT_NAME, StrategyAnalyzer
from app.ai_extraction.parser import DocumentParser
from tests.ai_extraction.conftest import SAMPLE_MARKDOWN


def test_analyzer_detects_title_and_description() -> None:
    parsed = DocumentParser().parse(SAMPLE_MARKDOWN)
    overview = StrategyAnalyzer().analyze(parsed)
    assert overview.name == "Golden Cross Trend Strategy"
    assert overview.name_detected is True
    assert "trend-following" in overview.description
    assert overview.description_detected is True


def test_description_never_duplicates_the_title() -> None:
    parsed = DocumentParser().parse(SAMPLE_MARKDOWN)
    overview = StrategyAnalyzer().analyze(parsed)
    assert overview.description != overview.name
    assert not overview.description.lstrip("#").strip() == overview.name


def test_no_title_falls_back_to_default_name() -> None:
    parsed = DocumentParser().parse("")
    overview = StrategyAnalyzer().analyze(parsed)
    assert overview.name == DEFAULT_NAME
    assert overview.name_detected is False


def test_no_description_reports_not_detected() -> None:
    parsed = DocumentParser().parse("# Only A Title")
    overview = StrategyAnalyzer().analyze(parsed)
    assert overview.description == ""
    assert overview.description_detected is False


def test_long_title_and_description_are_truncated() -> None:
    long_title = "A" * 300
    long_desc = "B" * 1000
    parsed = DocumentParser().parse(f"{long_title}\n\n{long_desc}")
    overview = StrategyAnalyzer().analyze(parsed)
    assert len(overview.name) <= 120
    assert len(overview.description) <= 500
