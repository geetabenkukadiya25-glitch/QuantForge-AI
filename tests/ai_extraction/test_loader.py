"""`DocumentLoader`: source-type-aware, deterministic text normalization."""

from app.ai_extraction.loader import DocumentLoader
from app.ai_extraction.models import SourceType


def test_youtube_timestamps_are_stripped() -> None:
    content = DocumentLoader().load("00:12 Welcome to the strategy 01:23:45 more text", SourceType.YOUTUBE_TRANSCRIPT)
    assert "00:12" not in content.normalized_text
    assert "01:23:45" not in content.normalized_text


def test_pine_script_line_comments_are_stripped() -> None:
    content = DocumentLoader().load("sma = ta.sma(close, 20) // fast moving average", SourceType.PINE_SCRIPT)
    assert "fast moving average" not in content.normalized_text
    assert "ta.sma" in content.normalized_text


def test_mql_block_comments_are_stripped() -> None:
    content = DocumentLoader().load("/* strategy header */\ndouble sl = 20;", SourceType.MQL5)
    assert "strategy header" not in content.normalized_text
    assert "double sl" in content.normalized_text


def test_easylanguage_block_comments_are_stripped() -> None:
    content = DocumentLoader().load("{ this is a comment }\nBuy next bar at market;", SourceType.EASYLANGUAGE)
    assert "this is a comment" not in content.normalized_text
    assert "Buy next bar" in content.normalized_text


def test_markdown_strips_emphasis_but_preserves_underscores() -> None:
    content = DocumentLoader().load("**Buy** when `fast_ma` crosses *slow_ma*", SourceType.MARKDOWN)
    assert "fast_ma" in content.normalized_text
    assert "slow_ma" in content.normalized_text
    assert "**" not in content.normalized_text
    assert "`" not in content.normalized_text


def test_ocr_collapses_repeated_whitespace() -> None:
    content = DocumentLoader().load("Entry    when    RSI   is   low", SourceType.OCR_TEXT)
    assert "    " not in content.normalized_text


def test_plain_text_passes_through_mostly_unchanged() -> None:
    content = DocumentLoader().load("Buy when price breaks above resistance.", SourceType.PLAIN_TEXT)
    assert "Buy when price breaks above resistance." in content.normalized_text


def test_line_count_reflects_normalized_text() -> None:
    content = DocumentLoader().load("line one\nline two\nline three", SourceType.PLAIN_TEXT)
    assert content.line_count == 3


def test_empty_input_does_not_raise() -> None:
    content = DocumentLoader().load("   ", SourceType.PLAIN_TEXT)
    assert content.normalized_text  # min_length=1 satisfied, not empty
