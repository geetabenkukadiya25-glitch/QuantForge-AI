"""Credential REQUIREMENT description only (Phase 17.9) -- NEVER
credential storage. This module describes what field NAMES a real future
provider would eventually need to ask a user for (e.g. GitHub -> a
token); it never accepts, stores, logs, or returns an actual secret
VALUE. There is deliberately no `store_credential`/`get_credential`/
`set_credential` function anywhere in this file or package -- nothing to
store, nothing stored, nothing read back.
"""

from dataclasses import dataclass, field

_REQUIRED_FIELDS: dict[str, list[str]] = {
    "github": ["token"],
    "s3": ["access_key_id", "secret_access_key", "region", "bucket"],
    "azure_blob": ["account_name", "account_key", "container"],
    "google_drive": ["client_id", "client_secret", "refresh_token"],
    "dropbox": ["access_token"],
    "generic_rest": ["base_url", "api_key"],
}


@dataclass(frozen=True)
class CredentialRequirement:
    provider_id: str
    required_field_names: list[str] = field(default_factory=list)


def describe_credential_requirements(provider_id: str) -> CredentialRequirement:
    """Field NAMES only -- never a value, never a default, never
    something that could be mistaken for an actual secret."""
    return CredentialRequirement(provider_id=provider_id, required_field_names=list(_REQUIRED_FIELDS.get(provider_id, [])))
