"""Tests for IndicatorSerializer."""

import json

import yaml

from app.indicator_engine.serializer import IndicatorSerializer


def test_to_json_round_trip(engine, context) -> None:
    result = engine.compute("SMA", context)
    serializer = IndicatorSerializer()
    text = serializer.to_json(result)
    data = json.loads(text)
    assert data["indicator_name"] == "SMA"


def test_to_yaml_is_valid(engine, context) -> None:
    result = engine.compute("SMA", context)
    text = IndicatorSerializer().to_yaml(result)
    data = yaml.safe_load(text)
    assert data["indicator_name"] == "SMA"


def test_canonical_json_is_deterministic(engine, context) -> None:
    result = engine.compute("SMA", context)
    serializer = IndicatorSerializer()
    a = serializer.to_json(result, canonical=True)
    b = serializer.to_json(result, canonical=True)
    assert a == b


def test_metadata_to_dict(engine) -> None:
    metadata = engine.registry.get_metadata("SMA")
    data = IndicatorSerializer().metadata_to_dict(metadata)
    assert data["name"] == "SMA"
    assert "parameters" in data


def test_metadata_to_json_is_json_safe(engine) -> None:
    metadata = engine.registry.get_metadata("RSI")
    text = IndicatorSerializer().metadata_to_json(metadata)
    json.loads(text)  # must not raise
