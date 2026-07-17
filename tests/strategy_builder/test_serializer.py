"""Tests for StrategySerializer."""

import json

import yaml

from app.strategy_builder.builder import StrategyBuilder
from app.strategy_builder.serializer import StrategySerializer


def test_to_dict_is_json_safe(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    data = StrategySerializer().to_dict(model)
    json.dumps(data)  # must not raise


def test_to_json_round_trip(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    serializer = StrategySerializer()
    text = serializer.to_json(model)
    from app.strategy_builder.models import StrategyModel

    reloaded = StrategyModel.model_validate(json.loads(text))
    assert reloaded == model


def test_to_yaml_round_trip(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    serializer = StrategySerializer()
    text = serializer.to_yaml(model)
    from app.strategy_builder.models import StrategyModel

    reloaded = StrategyModel.model_validate(yaml.safe_load(text))
    assert reloaded == model


def test_canonical_json_is_deterministic(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    serializer = StrategySerializer()
    a = serializer.to_json(model, canonical=True)
    b = serializer.to_json(model, canonical=True)
    assert a == b


def test_pretty_json_has_newlines(valid_context) -> None:
    model = StrategyBuilder().build(valid_context)
    text = StrategySerializer().to_json(model, pretty=True)
    assert "\n" in text
