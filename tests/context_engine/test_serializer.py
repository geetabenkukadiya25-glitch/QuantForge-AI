"""Tests for ContextSerializer."""

import json

import yaml

from app.context_engine.serializer import ContextSerializer


def test_to_dict_is_json_safe(snapshot) -> None:
    data = ContextSerializer().to_dict(snapshot)
    json.dumps(data)  # must not raise


def test_to_json_round_trip(snapshot) -> None:
    serializer = ContextSerializer()
    text = serializer.to_json(snapshot)
    reloaded = serializer.from_dict(json.loads(text))
    assert reloaded == snapshot


def test_to_yaml_round_trip(snapshot) -> None:
    serializer = ContextSerializer()
    text = serializer.to_yaml(snapshot)
    reloaded = serializer.from_dict(yaml.safe_load(text))
    assert reloaded == snapshot


def test_canonical_json_is_deterministic(snapshot) -> None:
    serializer = ContextSerializer()
    a = serializer.to_json(snapshot, canonical=True)
    b = serializer.to_json(snapshot, canonical=True)
    assert a == b


def test_pretty_json_has_newlines(snapshot) -> None:
    text = ContextSerializer().to_json(snapshot, pretty=True)
    assert "\n" in text


def test_compact_json_has_no_newlines(snapshot) -> None:
    text = ContextSerializer().to_json(snapshot, pretty=False)
    assert "\n" not in text
