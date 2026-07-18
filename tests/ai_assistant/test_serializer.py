"""Tests for `AssistantSerializer`."""

import json

import yaml

from app.ai_assistant.runner import AssistantRunner
from app.ai_assistant.serializer import AssistantSerializer
from tests.ai_assistant.conftest import make_context


def _result(full_context):
    context = make_context(full_context, "Explain optimization")
    return AssistantRunner().execute(context)


def test_to_dict_is_json_safe(full_context):
    result = _result(full_context)
    data = AssistantSerializer().to_dict(result)
    json.dumps(data)
    assert data["result_id"] == result.result_id


def test_to_json_round_trips(full_context):
    result = _result(full_context)
    text = AssistantSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_deterministic(full_context):
    result = _result(full_context)
    serializer = AssistantSerializer()
    assert serializer.to_json(result, canonical=True) == serializer.to_json(result, canonical=True)


def test_to_yaml_round_trips(full_context):
    result = _result(full_context)
    text = AssistantSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_has_no_newlines(full_context):
    result = _result(full_context)
    canonical = AssistantSerializer().to_json(result, canonical=True)
    assert "\n" not in canonical
