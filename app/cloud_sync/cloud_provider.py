"""Abstract cloud provider interface (Phase 17.9) -- future foundation
only. `CloudProvider` defines the shape a REAL provider would someday
implement; every method here unconditionally raises `NotImplementedError`.
There is no fake success path anywhere in this module: no method returns
a placeholder result, no method performs any I/O, and no subclass below
overrides any of them. This file must never import `requests`, `httpx`,
`socket`, `boto3`, or any other network-capable library.
"""


class CloudProvider:
    """Base interface every future real provider (GitHub, S3, Azure Blob,
    Google Drive, Dropbox, a generic REST backend, ...) would subclass
    and actually implement. Today, every method raises immediately --
    instantiating this class or any of the placeholder subclasses below
    is safe (pure metadata), but calling any interface method is not
    supported and says so explicitly."""

    display_name: str = "Cloud Provider"
    description: str = "Abstract cloud provider interface -- not implemented."

    def _not_implemented(self, method_name: str) -> NotImplementedError:
        return NotImplementedError(f"{type(self).__name__}.{method_name}() is not implemented -- Cloud Sync Foundation provides no real cloud connectivity.")

    def connect(self) -> None:
        raise self._not_implemented("connect")

    def disconnect(self) -> None:
        raise self._not_implemented("disconnect")

    def upload(self, local_ref: str, remote_ref: str) -> None:
        raise self._not_implemented("upload")

    def download(self, remote_ref: str, local_ref: str) -> None:
        raise self._not_implemented("download")

    def delete(self, remote_ref: str) -> None:
        raise self._not_implemented("delete")

    def list(self, prefix: str = "") -> "list[str]":
        # Return annotation is a string literal deliberately -- a method
        # named `list` inside this class would otherwise shadow the
        # builtin `list` when Python lazily evaluates `list[str]` as a
        # real annotation (PEP 649), raising a confusing `TypeError`
        # from any introspection tool that reads it.
        raise self._not_implemented("list")

    def sync(self, local_ref: str, remote_ref: str) -> None:
        raise self._not_implemented("sync")

    def status(self) -> str:
        raise self._not_implemented("status")

    def validate(self) -> list[str]:
        raise self._not_implemented("validate")


class GitHubProvider(CloudProvider):
    display_name = "GitHub"
    description = "Would sync artifacts to a GitHub repository via the GitHub API. Not implemented -- no network code exists."


class S3Provider(CloudProvider):
    display_name = "AWS S3"
    description = "Would sync artifacts to an S3 bucket. Not implemented -- no network code exists."


class AzureBlobProvider(CloudProvider):
    display_name = "Azure Blob Storage"
    description = "Would sync artifacts to an Azure Blob container. Not implemented -- no network code exists."


class GoogleDriveProvider(CloudProvider):
    display_name = "Google Drive"
    description = "Would sync artifacts to a Google Drive folder. Not implemented -- no network code exists."


class DropboxProvider(CloudProvider):
    display_name = "Dropbox"
    description = "Would sync artifacts to a Dropbox folder. Not implemented -- no network code exists."


class GenericRestProvider(CloudProvider):
    display_name = "Generic REST"
    description = "Would sync artifacts to any REST-compatible backend. Not implemented -- no network code exists."
