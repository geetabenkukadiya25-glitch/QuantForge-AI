"""`ReplaySerializer`: to_dict/to_json/to_yaml round-trip the same content."""

import json

import yaml

from app.replay_engine.runner import ReplayRunner
from app.replay_engine.serializer import ReplaySerializer


def test_to_dict_is_json_safe(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    data = ReplaySerializer().to_dict(result)
    assert data["result_id"] == result.result_id
    assert data["checksum"] == result.checksum


def test_to_json_round_trips(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    text = ReplaySerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_stable(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    a = ReplaySerializer().to_json(result, canonical=True)
    b = ReplaySerializer().to_json(result, canonical=True)
    assert a == b


def test_to_yaml_round_trips(replay_context) -> None:
    result = ReplayRunner().execute(replay_context)
    text = ReplaySerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum
