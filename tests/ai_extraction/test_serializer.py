"""`ExtractionSerializer`: to_dict/to_json/to_yaml round-trip the same content."""

import json

import yaml

from app.ai_extraction.runner import ExtractionRunner
from app.ai_extraction.serializer import ExtractionSerializer


def test_to_dict_is_json_safe(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    data = ExtractionSerializer().to_dict(result)
    assert data["result_id"] == result.result_id
    assert data["checksum"] == result.checksum


def test_to_json_round_trips(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    text = ExtractionSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_stable(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    a = ExtractionSerializer().to_json(result, canonical=True)
    b = ExtractionSerializer().to_json(result, canonical=True)
    assert a == b


def test_to_yaml_round_trips(extraction_context) -> None:
    result = ExtractionRunner().execute(extraction_context)
    text = ExtractionSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum
