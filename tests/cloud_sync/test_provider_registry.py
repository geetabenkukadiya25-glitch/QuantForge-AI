"""`provider_registry.py` -- registration only, no instantiation/connection."""

from app.cloud_sync.cloud_provider import GitHubProvider
from app.cloud_sync.provider_registry import DEFAULT_REGISTRY, ProviderRegistry


def test_default_registry_has_six_providers() -> None:
    providers = DEFAULT_REGISTRY.list_providers()
    assert len(providers) == 6
    ids = {"github", "s3", "azure_blob", "google_drive", "dropbox", "generic_rest"}
    assert {DEFAULT_REGISTRY.get(pid).provider_id for pid in ids} == ids


def test_get_unknown_provider_returns_none() -> None:
    assert DEFAULT_REGISTRY.get("nonexistent") is None


def test_register_custom_provider() -> None:
    registry = ProviderRegistry()
    descriptor = registry.register("github", GitHubProvider)
    assert descriptor.provider_cls is GitHubProvider
    assert descriptor.display_name == GitHubProvider.display_name
    assert registry.get("github") is descriptor


def test_list_providers_sorted_by_display_name() -> None:
    names = [d.display_name for d in DEFAULT_REGISTRY.list_providers()]
    assert names == sorted(names)
