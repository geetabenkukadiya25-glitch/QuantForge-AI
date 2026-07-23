"""Version compatibility checks (Phase 19.0) -- feeds the
`UNSUPPORTED_VERSION` connection state. Pure comparison logic, no I/O of
its own (callers pass in already-fetched version info).
"""

from dataclasses import dataclass

# The package version this layer was built and verified against.
# Terminal builds are checked against a broad floor rather than a tight
# range, since MetaQuotes ships frequent, generally-compatible builds.
SUPPORTED_PACKAGE_VERSION = "5.0.5735"
MIN_SUPPORTED_TERMINAL_BUILD = 3000


@dataclass(frozen=True)
class CompatibilityResult:
    package_version: str
    package_supported: bool
    terminal_build: int | None
    terminal_supported: bool | None  # None when terminal_build is unknown (not connected)
    notes: list[str]


def check_package_version(installed_version: str) -> bool:
    return installed_version == SUPPORTED_PACKAGE_VERSION


def check_terminal_build(build: int) -> bool:
    return build >= MIN_SUPPORTED_TERMINAL_BUILD


def evaluate(installed_version: str, terminal_build: int | None) -> CompatibilityResult:
    notes: list[str] = []
    package_supported = check_package_version(installed_version)
    if not package_supported:
        notes.append(f"Installed MetaTrader5 package version {installed_version} differs from the verified {SUPPORTED_PACKAGE_VERSION} -- may still work, not guaranteed.")

    terminal_supported: bool | None = None
    if terminal_build is not None:
        terminal_supported = check_terminal_build(terminal_build)
        if not terminal_supported:
            notes.append(f"Terminal build {terminal_build} is below the minimum verified build {MIN_SUPPORTED_TERMINAL_BUILD}.")

    return CompatibilityResult(
        package_version=installed_version,
        package_supported=package_supported,
        terminal_build=terminal_build,
        terminal_supported=terminal_supported,
        notes=notes,
    )
