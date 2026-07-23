"""`cloud_provider.py` -- every method on every placeholder provider
class raises `NotImplementedError`. No fake implementation anywhere.

Calls are made with hardcoded argument counts per method (rather than
via `inspect.signature` introspection) so this test doesn't depend on
how each method's parameters happen to be annotated."""

import pytest

from app.cloud_sync.cloud_provider import (
    AzureBlobProvider,
    CloudProvider,
    DropboxProvider,
    GenericRestProvider,
    GitHubProvider,
    GoogleDriveProvider,
    S3Provider,
)

_ALL_PROVIDERS = [CloudProvider, GitHubProvider, S3Provider, AzureBlobProvider, GoogleDriveProvider, DropboxProvider, GenericRestProvider]
_INTERFACE_CALLS: dict[str, tuple] = {
    "connect": (),
    "disconnect": (),
    "upload": ("local", "remote"),
    "download": ("remote", "local"),
    "delete": ("remote",),
    "list": (),
    "sync": ("local", "remote"),
    "status": (),
    "validate": (),
}


@pytest.mark.parametrize("provider_cls", _ALL_PROVIDERS)
def test_every_interface_method_raises_not_implemented(provider_cls) -> None:
    provider = provider_cls()
    for method_name, args in _INTERFACE_CALLS.items():
        method = getattr(provider, method_name)
        with pytest.raises(NotImplementedError):
            method(*args)


def test_placeholder_subclasses_have_descriptive_metadata() -> None:
    for provider_cls in _ALL_PROVIDERS[1:]:  # skip base CloudProvider
        assert provider_cls.display_name
        assert provider_cls.description
        assert provider_cls.display_name != CloudProvider.display_name


def test_instantiation_is_safe_pure_metadata() -> None:
    # Constructing a provider must never raise or perform I/O.
    for provider_cls in _ALL_PROVIDERS:
        provider_cls()
