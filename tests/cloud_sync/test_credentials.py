"""`credentials.py` -- describes field NAMES only, never a value; there
is no store/get function to even attempt storing a secret."""

import app.cloud_sync.credentials as credentials_module
from app.cloud_sync.credentials import describe_credential_requirements


def test_github_requirement_field_names_only() -> None:
    requirement = describe_credential_requirements("github")
    assert requirement.required_field_names == ["token"]


def test_unknown_provider_returns_empty_requirement() -> None:
    requirement = describe_credential_requirements("nonexistent")
    assert requirement.required_field_names == []


def test_no_store_or_get_function_exists() -> None:
    names = dir(credentials_module)
    assert not any(name.startswith("store_credential") or name.startswith("get_credential") or name.startswith("set_credential") for name in names)


def test_no_field_value_ever_present_only_names() -> None:
    for provider_id in ("github", "s3", "azure_blob", "google_drive", "dropbox", "generic_rest"):
        requirement = describe_credential_requirements(provider_id)
        for field_name in requirement.required_field_names:
            assert isinstance(field_name, str) and field_name.islower()
