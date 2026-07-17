"""`ValidationSerializer`."""

import json

import yaml

from app.validation_engine.runner import ValidationRunner
from app.validation_engine.serializer import ValidationSerializer


def test_to_dict_round_trips_key_fields(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    data = ValidationSerializer().to_dict(result)
    assert data["checksum"] == result.checksum


def test_to_json_is_valid_json(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    text = ValidationSerializer().to_json(result)
    assert json.loads(text)["checksum"] == result.checksum


def test_to_json_canonical_is_sorted_and_compact(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    text = ValidationSerializer().to_json(result, canonical=True)
    assert "\n" not in text


def test_to_yaml_is_valid_yaml(validation_context) -> None:
    result = ValidationRunner().execute(validation_context)
    text = ValidationSerializer().to_yaml(result)
    assert yaml.safe_load(text)["checksum"] == result.checksum
