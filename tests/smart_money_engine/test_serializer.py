"""Tests for SMCSerializer."""

import json

import yaml

from app.smart_money_engine.serializer import SMCSerializer


def test_to_json_round_trip(engine, context) -> None:
    result = engine.detect("Swing High", context)
    serializer = SMCSerializer()
    text = serializer.to_json(result)
    data = json.loads(text)
    assert data["detector_name"] == "Swing High"


def test_to_yaml_is_valid(engine, context) -> None:
    result = engine.detect("Swing High", context)
    text = SMCSerializer().to_yaml(result)
    data = yaml.safe_load(text)
    assert data["detector_name"] == "Swing High"


def test_canonical_json_is_deterministic(engine, context) -> None:
    result = engine.detect("Swing High", context)
    serializer = SMCSerializer()
    a = serializer.to_json(result, canonical=True)
    b = serializer.to_json(result, canonical=True)
    assert a == b


def test_metadata_to_dict(engine) -> None:
    metadata = engine.registry.get_metadata("Swing High")
    data = SMCSerializer().metadata_to_dict(metadata)
    assert data["name"] == "Swing High"
    assert "parameters" in data


def test_metadata_to_json_is_json_safe(engine) -> None:
    metadata = engine.registry.get_metadata("Fair Value Gap")
    text = SMCSerializer().metadata_to_json(metadata)
    json.loads(text)  # must not raise
