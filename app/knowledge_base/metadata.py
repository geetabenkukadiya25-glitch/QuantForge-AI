"""Static, self-describing identity for a completed knowledge base build."""

from pydantic import BaseModel, ConfigDict, Field

KNOWLEDGE_RESULT_VERSION = "1.0.0"


class KnowledgeMetadata(BaseModel):
    """Identity and versioning information carried onto a `KnowledgeResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    knowledge_id: str = Field(min_length=1, description="Unique id for this specific knowledge base build.")
    entry_count: int = Field(ge=0, description="How many KnowledgeEntry records this build compiled.")
    category_count: int = Field(ge=0, description="How many distinct KnowledgeCategory values are represented.")
    result_version: str = Field(default=KNOWLEDGE_RESULT_VERSION, description="KnowledgeResult schema version.")
