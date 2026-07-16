"""Tests for SchemaManager."""

import pytest

from app.sdl.schema_manager import SchemaManager


def test_get_sdl_version() -> None:
    assert SchemaManager().get_sdl_version() == "1.0.0"


def test_get_sections_includes_all_spec_sections() -> None:
    sections = SchemaManager().get_sections()
    expected = {
        "metadata",
        "market",
        "symbols",
        "timeframes",
        "sessions",
        "bias",
        "filters",
        "indicators",
        "entry_rules",
        "exit_rules",
        "risk_management",
        "position_sizing",
        "trade_management",
        "news_rules",
        "spread_rules",
        "time_rules",
        "execution_rules",
        "scoring_rules",
        "alerts",
        "tags",
        "notes",
    }
    assert expected.issubset(set(sections))


def test_get_required_sections() -> None:
    required = SchemaManager().get_required_sections()
    assert "metadata" in required
    assert "market" in required
    assert "notes" not in required


def test_get_json_schema_has_properties() -> None:
    schema = SchemaManager().get_json_schema()
    assert "properties" in schema
    assert "metadata" in schema["properties"]


def test_describe_section_returns_metadata() -> None:
    info = SchemaManager().describe_section("metadata")
    assert info["section"] == "metadata"
    assert info["required"] is True


def test_describe_unknown_section_raises() -> None:
    with pytest.raises(KeyError):
        SchemaManager().describe_section("not_a_section")
