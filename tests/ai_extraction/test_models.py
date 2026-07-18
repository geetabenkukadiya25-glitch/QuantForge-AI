"""Frozen/immutable, hashable, versioned model behavior for ai_extraction models."""

import pytest
from pydantic import ValidationError

from app.ai_extraction.metadata import EXTRACTION_RESULT_VERSION, ExtractionMetadata
from app.ai_extraction.models import (
    CategoryConfidence,
    ConfidenceReport,
    ExtractionConfiguration,
    IndicatorMention,
    MissingInformationReport,
    SourceType,
)


def test_source_type_has_every_requested_source() -> None:
    expected = {"YOUTUBE_TRANSCRIPT", "PDF", "MARKDOWN", "PLAIN_TEXT", "PINE_SCRIPT", "MQL4", "MQL5", "EASYLANGUAGE", "PSEUDOCODE", "OCR_TEXT"}
    assert {s.value for s in SourceType} == expected


def test_extraction_configuration_is_frozen_and_hashable() -> None:
    config = ExtractionConfiguration()
    with pytest.raises(ValidationError):
        config.min_confidence_threshold = 0.9
    hash(config)


def test_extraction_configuration_defaults() -> None:
    config = ExtractionConfiguration()
    assert config.min_confidence_threshold == 0.3
    assert config.max_snippet_length == 200
    assert config.strategy_name_hint is None


def test_indicator_mention_is_frozen_and_hashable() -> None:
    mention = IndicatorMention(matched_type="SMA", raw_text="uses SMA", line_number=0, confidence=0.9)
    with pytest.raises(ValidationError):
        mention.confidence = 0.1
    hash(mention)


def test_indicator_mention_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=0.9, bogus=True)


def test_confidence_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        IndicatorMention(matched_type="SMA", raw_text="x", line_number=0, confidence=1.5)


def test_category_confidence_and_report() -> None:
    report = ConfidenceReport(overall_confidence=0.8, category_confidences=(CategoryConfidence(category="indicators", score=0.9, item_count=3),))
    assert report.overall_confidence == 0.8
    hash(report)


def test_missing_information_report_defaults() -> None:
    report = MissingInformationReport()
    assert report.missing_items == ()
    assert report.warnings == ()


def test_extraction_metadata_default_version() -> None:
    metadata = ExtractionMetadata(extraction_id="e1", source_type="MARKDOWN", source_checksum="abc123")
    assert metadata.result_version == EXTRACTION_RESULT_VERSION
