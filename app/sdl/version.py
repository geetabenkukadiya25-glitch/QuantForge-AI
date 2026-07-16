"""SDL and strategy versioning.

`SDL_VERSION` is the version of the *schema* (this module). A strategy
document additionally carries its own `strategy_version` (see
`app.sdl.models.Metadata`), which is independent -- two strategies can
share an SDL version while being at different revisions of themselves.
"""

from dataclasses import dataclass

from app.sdl.exceptions import SDLVersionError

SDL_VERSION = "1.0.0"
SUPPORTED_SDL_VERSIONS = ["1.0.0"]


@dataclass(frozen=True)
class SemVer:
    """A minimal `major.minor.patch` version, comparable without extra dependencies."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version: str) -> "SemVer":
        parts = version.strip().split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise SDLVersionError(f"Invalid version string: {version!r} (expected 'X.Y.Z')")
        major, minor, patch = (int(part) for part in parts)
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "SemVer") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class VersionManager:
    """Checks SDL version compatibility and provides a migration hook."""

    def __init__(self, supported_versions: list[str] | None = None) -> None:
        self.supported_versions = supported_versions or SUPPORTED_SDL_VERSIONS

    def is_supported(self, version: str) -> bool:
        """Return True if `version` is a supported SDL version."""
        return version in self.supported_versions

    def compare(self, version_a: str, version_b: str) -> int:
        """Return -1, 0, or 1 as `version_a` is less than, equal to, or greater than `version_b`."""
        a, b = SemVer.parse(version_a), SemVer.parse(version_b)
        if a < b:
            return -1
        if b < a:
            return 1
        return 0

    def latest_supported(self) -> str:
        """Return the highest supported SDL version."""
        return max(self.supported_versions, key=SemVer.parse)

    def migrate(self, data: dict, from_version: str, to_version: str) -> dict:
        """Migrate a raw strategy document from `from_version` to `to_version`.

        Only a same-version no-op is currently supported; cross-version
        migration will be implemented once a second SDL version exists.

        Raises:
            SDLVersionError: if either version is unsupported, or a real
                (non-identity) migration is requested.
        """
        if not self.is_supported(from_version):
            raise SDLVersionError(f"Unsupported source SDL version: {from_version!r}")
        if not self.is_supported(to_version):
            raise SDLVersionError(f"Unsupported target SDL version: {to_version!r}")
        if from_version == to_version:
            return data
        raise SDLVersionError(
            f"No migration path from {from_version!r} to {to_version!r} yet "
            "(only one SDL version currently exists)."
        )
