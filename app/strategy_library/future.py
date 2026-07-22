"""Forward-looking interfaces only (Phase 18 rule 30) -- NOT implemented,
NOT wired into `StrategyLibraryManager` or any UI. These `Protocol`s exist
purely so a future phase can add a concrete implementation (e.g. a Git-
backed or cloud-backed sync provider) without reshaping the manager's
public surface. Adding a real implementation is future work; see
`PROJECT_IDEAS.md`.
"""

from pathlib import Path
from typing import Protocol

from app.sdl.models import StrategyDefinition


class RemoteSyncProvider(Protocol):
    """A future push/pull backend for a strategy library: Git, a cloud
    bucket, a team server, or a marketplace. `StrategyLibraryManager`
    remains fully functional with no provider configured (offline-first);
    a provider would be an optional, injected collaborator, never a
    required dependency."""

    def push(self, path: Path, definition: StrategyDefinition) -> str:
        """Publish a local strategy to the remote; returns a remote reference."""
        ...

    def pull(self, remote_reference: str) -> StrategyDefinition:
        """Fetch a strategy from the remote by its reference."""
        ...

    def list_remote(self) -> list[str]:
        """List available remote references (e.g. marketplace listings, team strategies)."""
        ...


class CollaborationProvider(Protocol):
    """A future real-time/team-editing backend (presence, comments,
    shared locks across machines -- as opposed to `app.strategy_library.lock`,
    which is intentionally single-machine only)."""

    def announce_presence(self, key: str, user: str) -> None: ...

    def list_active_editors(self, key: str) -> list[str]: ...


class AIStrategyGenerator(Protocol):
    """A future AI-assisted strategy authoring backend -- distinct from
    the existing `app.ai_extraction`/`app.ai_assistant` modules, which
    this interface would eventually delegate to rather than duplicate."""

    def generate(self, prompt: str) -> StrategyDefinition: ...
