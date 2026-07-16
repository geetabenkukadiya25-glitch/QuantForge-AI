"""Tests for StrategySerializer (JSON/YAML, pretty, canonical, round-trip)."""

import json

import yaml

from app.sdl.models import StrategyDefinition
from app.sdl.parser import StrategyParser
from app.sdl.serializer import StrategySerializer


def test_to_dict_is_json_safe(full_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(full_strategy_dict)
    data = StrategySerializer().to_dict(definition)
    json.dumps(data)  # must not raise


def test_to_json_round_trip(full_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(full_strategy_dict)
    serializer = StrategySerializer()
    text = serializer.to_json(definition)
    reloaded = serializer.from_dict(json.loads(text))
    assert reloaded == definition


def test_to_yaml_round_trip(full_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(full_strategy_dict)
    serializer = StrategySerializer()
    text = serializer.to_yaml(definition)
    reloaded = serializer.from_dict(yaml.safe_load(text))
    assert reloaded == definition


def test_to_json_pretty_has_newlines(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    text = StrategySerializer().to_json(definition, pretty=True)
    assert "\n" in text


def test_to_json_compact_has_no_indentation_whitespace(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    text = StrategySerializer().to_json(definition, pretty=False)
    assert "\n" not in text


def test_canonical_json_is_deterministic_regardless_of_field_order(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    serializer = StrategySerializer()
    text_a = serializer.to_json(definition, canonical=True)
    text_b = serializer.to_json(definition, canonical=True)
    assert text_a == text_b
    assert json.loads(text_a) == json.loads(text_a)  # sanity: valid JSON


def test_canonical_yaml_sorts_keys(minimal_strategy_dict) -> None:
    definition = StrategyDefinition.model_validate(minimal_strategy_dict)
    text = StrategySerializer().to_yaml(definition, canonical=True)
    top_level_keys = [line for line in text.splitlines() if line and not line.startswith((" ", "-"))]
    keys = [line.split(":")[0] for line in top_level_keys]
    assert keys == sorted(keys)


def test_round_trip_through_parser_and_serializer(example_path) -> None:
    data = StrategyParser().parse_file(example_path)
    definition = StrategyDefinition.model_validate(data)
    serializer = StrategySerializer()

    yaml_text = serializer.to_yaml(definition)
    reparsed = StrategyParser().parse_yaml(yaml_text)
    reloaded = serializer.from_dict(reparsed)

    assert reloaded == definition
