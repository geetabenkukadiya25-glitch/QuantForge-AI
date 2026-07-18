"""Determinism: two `AIStrategyExtractionEngine.execute()` calls over the same
input text must produce the same checksum -- proving no random identity
field leaked into the checksummed payload (the recurring bug class caught
in Phases 9-14).
"""

from app.ai_extraction.engine import AIStrategyExtractionEngine
from app.ai_extraction.models import SourceType
from tests.ai_extraction.conftest import SAMPLE_MARKDOWN


def test_two_runs_of_the_same_text_produce_the_same_checksum(indicator_registry, smc_registry) -> None:
    engine = AIStrategyExtractionEngine()
    result1 = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    result2 = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert result1.checksum == result2.checksum
    assert result1.result_id != result2.result_id
    assert result1.metadata.extraction_id != result2.metadata.extraction_id


def test_every_extracted_category_is_identical_across_runs(indicator_registry, smc_registry) -> None:
    engine = AIStrategyExtractionEngine()
    result1 = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    result2 = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert result1.indicators == result2.indicators
    assert result1.entry_rules == result2.entry_rules
    assert result1.generated_sdl_yaml == result2.generated_sdl_yaml
    assert result1.confidence == result2.confidence


def test_different_source_type_for_the_same_text_changes_the_checksum(indicator_registry, smc_registry) -> None:
    engine = AIStrategyExtractionEngine()
    result_md = engine.execute(SAMPLE_MARKDOWN, SourceType.MARKDOWN, indicator_registry=indicator_registry, smc_registry=smc_registry)
    result_plain = engine.execute(SAMPLE_MARKDOWN, SourceType.PLAIN_TEXT, indicator_registry=indicator_registry, smc_registry=smc_registry)
    assert result_md.checksum != result_plain.checksum
