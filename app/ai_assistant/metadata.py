"""Static, self-describing identity for a completed assistant query."""

from pydantic import BaseModel, ConfigDict, Field

AI_ASSISTANT_RESULT_VERSION = "1.0.0"


class AssistantMetadata(BaseModel):
    """Identity and versioning information carried onto an `AssistantResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    assistant_id: str = Field(min_length=1, description="Unique id for this specific query/answer.")
    query_checksum: str = Field(min_length=1, description="SHA-256 of the raw query text, for cache/dedup purposes.")
    intent: str = Field(min_length=1, description="The classified QueryIntent value.")
    result_version: str = Field(default=AI_ASSISTANT_RESULT_VERSION, description="AssistantResult schema version.")
