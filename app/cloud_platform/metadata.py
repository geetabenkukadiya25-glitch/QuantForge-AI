"""Static, self-describing identity for a compiled Cloud Platform workspace.

Offline-only identity: `label` is a free-text display string, never an
authenticated user identity, credential, or session token -- this phase
implements no authentication, no networking, and no synchronization.
"""

from pydantic import BaseModel, ConfigDict, Field

CLOUD_PLATFORM_RESULT_VERSION = "1.0.0"
CLOUD_SCHEMA_VERSION = "1.0.0"


class WorkspaceMetadata(BaseModel):
    """Identity and versioning information carried onto a `CloudWorkspace`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    workspace_id: str = Field(min_length=1, description="Caller-supplied, stable identifier for this workspace.")
    schema_version: str = Field(default=CLOUD_SCHEMA_VERSION, description="CloudWorkspace schema version.")
    label: str = Field(default="", description="Free-text, offline display label. Not an identity or authentication credential.")
    result_version: str = Field(default=CLOUD_PLATFORM_RESULT_VERSION, description="CloudBuild schema version.")
