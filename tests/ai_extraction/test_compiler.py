"""`ExtractionCompiler`: deterministic checksum excludes identity/timestamp fields."""

from app.ai_extraction.runner import ExtractionRunner


def test_compile_produces_a_valid_result(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    assert result.checksum
    assert result.result_id
    assert result.metadata.source_type == "MARKDOWN"


def test_same_context_produces_the_same_checksum(extraction_context) -> None:
    result1 = ExtractionRunner().execute(extraction_context)
    result2 = ExtractionRunner().execute(extraction_context)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.extraction_id != result2.metadata.extraction_id


def test_different_text_produces_a_different_checksum(extraction_configuration) -> None:
    from app.ai_extraction.context import ExtractionContext
    from app.ai_extraction.models import SourceType

    context_a = ExtractionContext(raw_text="Buy when RSI crosses above 30 during a valid trading session today.", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)
    context_b = ExtractionContext(raw_text="Sell when RSI crosses below 70 during a valid trading session today.", source_type=SourceType.PLAIN_TEXT, configuration=extraction_configuration)

    result_a = ExtractionRunner().execute(context_a)
    result_b = ExtractionRunner().execute(context_b)
    assert result_a.checksum != result_b.checksum


def test_source_checksum_reflects_raw_text(extraction_context) -> None:
    import hashlib

    result = ExtractionRunner().execute(extraction_context)
    expected = hashlib.sha256(extraction_context.raw_text.encode("utf-8")).hexdigest()
    assert result.metadata.source_checksum == expected
