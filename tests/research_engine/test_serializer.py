"""`ResearchSerializer`: to_dict/to_json/to_yaml round-trip the same content."""

import json

import yaml

from app.research_engine.runner import ResearchRunner
from app.research_engine.serializer import ResearchSerializer


def test_to_dict_is_json_safe(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    data = ResearchSerializer().to_dict(result)
    assert data["result_id"] == result.result_id
    assert data["checksum"] == result.checksum


def test_to_json_round_trips(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    text = ResearchSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_stable(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    a = ResearchSerializer().to_json(result, canonical=True)
    b = ResearchSerializer().to_json(result, canonical=True)
    assert a == b


def test_to_yaml_round_trips(research_context) -> None:
    result = ResearchRunner().execute(research_context)
    text = ResearchSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum
