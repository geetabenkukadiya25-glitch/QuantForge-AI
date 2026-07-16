"""Market Context schema versioning.

Intentionally a separate, lightweight implementation from
`app.sdl.version` (which has its own `SemVer`/`VersionManager`) --
`context_engine` and `sdl` are independent engines and must not import
each other's internals, for the same reason `chart_engine` and
`data_engine` each keep their own small `TimeframeConverter`.
"""

from dataclasses import dataclass

from app.context_engine.exceptions import ContextVersionError

CONTEXT_VERSION = "1.0.0"
SUPPORTED_CONTEXT_VERSIONS = ["1.0.0"]


@dataclass(frozen=True)
class ContextSemVer:
    """A minimal `major.minor.patch` version, comparable without extra dependencies."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version: str) -> "ContextSemVer":
        parts = version.strip().split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            raise ContextVersionError(f"Invalid version string: {version!r} (expected 'X.Y.Z')")
        major, minor, patch = (int(part) for part in parts)
        return cls(major, minor, patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "ContextSemVer") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)


class ContextVersionManager:
    """Checks Market Context schema version compatibility and provides a migration hook."""

    def __init__(self, supported_versions: list[str] | None = None) -> None:
        self.supported_versions = supported_versions or SUPPORTED_CONTEXT_VERSIONS

    def is_supported(self, version: str) -> bool:
        """Return True if `version` is a supported context schema version."""
        return version in self.supported_versions

    def compare(self, version_a: str, version_b: str) -> int:
        """Return -1, 0, or 1 as `version_a` is less than, equal to, or greater than `version_b`."""
        a, b = ContextSemVer.parse(version_a), ContextSemVer.parse(version_b)
        if a < b:
            return -1
        if b < a:
            return 1
        return 0

    def latest_supported(self) -> str:
        """Return the highest supported context schema version."""
        return max(self.supported_versions, key=ContextSemVer.parse)

    def migrate(self, data: dict, from_version: str, to_version: str) -> dict:
        """Migrate a raw context document from `from_version` to `to_version`.

        Only a same-version no-op is currently supported -- only one
        context schema version exists today.

        Raises:
            ContextVersionError: if either version is unsupported, or a
                real (non-identity) migration is requested.
        """
        if not self.is_supported(from_version):
            raise ContextVersionError(f"Unsupported source context version: {from_version!r}")
        if not self.is_supported(to_version):
            raise ContextVersionError(f"Unsupported target context version: {to_version!r}")
        if from_version == to_version:
            return data
        raise ContextVersionError(
            f"No migration path from {from_version!r} to {to_version!r} yet "
            "(only one context schema version currently exists)."
        )
