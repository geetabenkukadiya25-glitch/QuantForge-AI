"""Tests for StrategyParser."""

import pytest

from app.sdl.exceptions import SDLParseError
from app.sdl.parser import StrategyParser


def test_parse_yaml_returns_dict() -> None:
    text = "metadata:\n  id: x\n  name: X\n"
    data = StrategyParser().parse_yaml(text)
    assert data == {"metadata": {"id": "x", "name": "X"}}


def test_parse_json_returns_dict() -> None:
    text = '{"metadata": {"id": "x", "name": "X"}}'
    data = StrategyParser().parse_json(text)
    assert data == {"metadata": {"id": "x", "name": "X"}}


def test_parse_invalid_yaml_raises() -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse_yaml("metadata: [unclosed")


def test_parse_invalid_json_raises() -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse_json("{not valid json")


def test_parse_non_mapping_yaml_raises() -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse_yaml("- a\n- b\n")


def test_parse_non_mapping_json_raises() -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse_json("[1, 2, 3]")


def test_parse_dispatches_by_format() -> None:
    parser = StrategyParser()
    assert parser.parse('{"a": 1}', "json") == {"a": 1}
    assert parser.parse("a: 1", "yaml") == {"a": 1}


def test_parse_unsupported_format_raises() -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse("a: 1", "xml")  # type: ignore[arg-type]


def test_parse_future_format_raises_descriptive_error() -> None:
    with pytest.raises(SDLParseError, match="future format"):
        StrategyParser().parse("a = 1", "toml")  # type: ignore[arg-type]


def test_parse_file_yaml(tmp_path) -> None:
    path = tmp_path / "strategy.yaml"
    path.write_text("metadata:\n  id: x\n  name: X\n", encoding="utf-8")
    data = StrategyParser().parse_file(path)
    assert data["metadata"]["id"] == "x"


def test_parse_file_json(tmp_path) -> None:
    path = tmp_path / "strategy.json"
    path.write_text('{"metadata": {"id": "x", "name": "X"}}', encoding="utf-8")
    data = StrategyParser().parse_file(path)
    assert data["metadata"]["id"] == "x"


def test_parse_file_missing_raises(tmp_path) -> None:
    with pytest.raises(SDLParseError):
        StrategyParser().parse_file(tmp_path / "does_not_exist.yaml")


def test_parse_file_unrecognized_extension_raises(tmp_path) -> None:
    path = tmp_path / "strategy.txt"
    path.write_text("metadata: {}", encoding="utf-8")
    with pytest.raises(SDLParseError):
        StrategyParser().parse_file(path)


def test_parse_all_bundled_examples(example_path) -> None:
    data = StrategyParser().parse_file(example_path)
    assert "metadata" in data
