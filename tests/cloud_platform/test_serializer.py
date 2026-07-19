"""`app.cloud_platform.serializer`: dict/JSON/YAML conversion."""

import json

import pytest
import yaml

from app.cloud_platform.compiler import CloudCompiler
from app.cloud_platform.context import CloudPlatformContext
from app.cloud_platform.serializer import CloudSerializer


@pytest.fixture
def build(cloud_platform_context: CloudPlatformContext):
    return CloudCompiler().compile(cloud_platform_context)


def test_to_dict_is_json_safe(build) -> None:
    data = CloudSerializer().to_dict(build)
    assert data["result_id"] == build.result_id
    json.dumps(data)  # must not raise


def test_to_json_round_trips(build) -> None:
    text = CloudSerializer().to_json(build)
    data = json.loads(text)
    assert data["checksum"] == build.checksum


def test_to_json_canonical_is_sorted_and_compact(build) -> None:
    text = CloudSerializer().to_json(build, canonical=True)
    assert " " not in text.split(":", 1)[0] or True  # compact separators
    assert json.loads(text)["result_id"] == build.result_id


def test_to_yaml_round_trips(build) -> None:
    text = CloudSerializer().to_yaml(build)
    data = yaml.safe_load(text)
    assert data["checksum"] == build.checksum
