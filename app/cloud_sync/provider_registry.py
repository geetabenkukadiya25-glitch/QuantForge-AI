"""Provider registration only (Phase 17.9) -- no provider is ever
instantiated, connected to, or invoked by this module. Registration
metadata (id, display name, description, provider class reference) is
all that's stored."""

from dataclasses import dataclass

from app.cloud_sync.cloud_provider import (
    AzureBlobProvider,
    CloudProvider,
    DropboxProvider,
    GenericRestProvider,
    GitHubProvider,
    GoogleDriveProvider,
    S3Provider,
)


@dataclass(frozen=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    description: str
    provider_cls: type[CloudProvider]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ProviderDescriptor] = {}

    def register(self, provider_id: str, provider_cls: type[CloudProvider], display_name: str | None = None, description: str | None = None) -> ProviderDescriptor:
        descriptor = ProviderDescriptor(
            provider_id=provider_id,
            display_name=display_name or provider_cls.display_name,
            description=description or provider_cls.description,
            provider_cls=provider_cls,
        )
        self._providers[provider_id] = descriptor
        return descriptor

    def get(self, provider_id: str) -> ProviderDescriptor | None:
        return self._providers.get(provider_id)

    def list_providers(self) -> list[ProviderDescriptor]:
        return sorted(self._providers.values(), key=lambda d: d.display_name)


def _build_default_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("github", GitHubProvider)
    registry.register("s3", S3Provider)
    registry.register("azure_blob", AzureBlobProvider)
    registry.register("google_drive", GoogleDriveProvider)
    registry.register("dropbox", DropboxProvider)
    registry.register("generic_rest", GenericRestProvider)
    return registry


DEFAULT_REGISTRY = _build_default_registry()
