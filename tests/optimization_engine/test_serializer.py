"""`OptimizationSerializer`."""

import json

import yaml

from app.optimization_engine.runner import OptimizationRunner
from app.optimization_engine.serializer import OptimizationSerializer


def test_to_dict_round_trips_key_fields(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    data = OptimizationSerializer().to_dict(result)
    assert data["checksum"] == result.checksum
    assert len(data["candidates"]) == len(result.candidates)


def test_to_json_is_valid_json(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    text = OptimizationSerializer().to_json(result)
    assert json.loads(text)["checksum"] == result.checksum


def test_to_json_canonical_is_sorted_and_compact(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    text = OptimizationSerializer().to_json(result, canonical=True)
    assert "\n" not in text


def test_to_yaml_is_valid_yaml(optimization_context) -> None:
    result = OptimizationRunner().execute(optimization_context)
    text = OptimizationSerializer().to_yaml(result)
    assert yaml.safe_load(text)["checksum"] == result.checksum
