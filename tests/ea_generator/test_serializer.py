"""Tests for app.ea_generator.serializer."""

import json

import yaml

from app.ea_generator.engine import EAGeneratorEngine
from app.ea_generator.serializer import EAGeneratorSerializer


def _result(strategy_model_a, ea_configuration):
    return EAGeneratorEngine().execute(strategy_model_a, ea_configuration)


def test_to_dict_is_json_safe(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    data = EAGeneratorSerializer().to_dict(result)
    json.dumps(data)  # must not raise


def test_to_dict_contains_source_code(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    data = EAGeneratorSerializer().to_dict(result)
    assert data["source_code"] == result.source_code


def test_to_json_round_trips(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    text = EAGeneratorSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_sorted_and_compact(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    text = EAGeneratorSerializer().to_json(result, canonical=True)
    assert "\n" not in text
    assert json.loads(text)["checksum"] == result.checksum


def test_to_yaml_round_trips(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    text = EAGeneratorSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum


def test_to_mq5_returns_raw_source(strategy_model_a, ea_configuration) -> None:
    result = _result(strategy_model_a, ea_configuration)
    assert EAGeneratorSerializer().to_mq5(result) == result.source_code
