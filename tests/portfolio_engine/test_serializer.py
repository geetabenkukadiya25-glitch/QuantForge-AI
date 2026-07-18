"""Tests for `PortfolioSerializer`."""

import json

import yaml

from app.portfolio_engine.runner import PortfolioRunner
from app.portfolio_engine.serializer import PortfolioSerializer


def test_to_dict_is_json_safe(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    data = PortfolioSerializer().to_dict(result)
    json.dumps(data)  # should not raise
    assert data["result_id"] == result.result_id


def test_to_json_round_trips(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    text = PortfolioSerializer().to_json(result)
    parsed = json.loads(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_sorted_and_compact(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    canonical = PortfolioSerializer().to_json(result, canonical=True)
    pretty = PortfolioSerializer().to_json(result, pretty=True)
    assert "\n" not in canonical
    assert len(canonical) < len(pretty)  # no structural whitespace, unlike the indented form
    assert json.loads(canonical)["result_id"] == result.result_id


def test_to_yaml_round_trips(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    text = PortfolioSerializer().to_yaml(result)
    parsed = yaml.safe_load(text)
    assert parsed["checksum"] == result.checksum


def test_to_json_canonical_is_deterministic(portfolio_context):
    result = PortfolioRunner().execute(portfolio_context)
    serializer = PortfolioSerializer()
    assert serializer.to_json(result, canonical=True) == serializer.to_json(result, canonical=True)
