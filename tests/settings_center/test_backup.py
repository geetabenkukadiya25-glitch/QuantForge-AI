"""`backup.py` -- export/import bytes round-trip, malformed-payload
rejection, and the "never silently drop a required section" guarantee."""

import json

import pytest

from app.settings_center.backup import export_bytes, parse_import_bytes, validate_import_payload
from app.settings_center.exceptions import SettingsImportError
from app.settings_center.settings_models import SettingsState


def test_export_bytes_round_trips_through_parse_import_bytes() -> None:
    state = SettingsState()
    state.risk.monte_carlo_iterations = 777
    payload = export_bytes(state)
    restored = parse_import_bytes(payload)
    assert restored.risk.monte_carlo_iterations == 777


def test_parse_import_bytes_rejects_invalid_json() -> None:
    with pytest.raises(SettingsImportError):
        parse_import_bytes(b"not json")


def test_parse_import_bytes_rejects_missing_sections() -> None:
    incomplete = json.dumps({"general": {}}).encode()
    with pytest.raises(SettingsImportError) as exc_info:
        parse_import_bytes(incomplete)
    assert any("workflow" in issue for issue in exc_info.value.issues)


def test_validate_import_payload_non_dict() -> None:
    assert validate_import_payload([1, 2, 3]) == ["payload must be a JSON object"]
