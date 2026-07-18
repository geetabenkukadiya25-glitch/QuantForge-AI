"""Static, self-describing identity for a completed strategy extraction."""

from pydantic import BaseModel, ConfigDict, Field

EXTRACTION_RESULT_VERSION = "1.0.0"


class ExtractionMetadata(BaseModel):
    """Identity and versioning information carried onto an `ExtractionResult`."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    extraction_id: str = Field(min_length=1, description="Unique id for this specific extraction run.")
    source_type: str = Field(min_length=1, description="The declared SourceType this document came from.")
    source_checksum: str = Field(min_length=1, description="SHA-256 of the raw input text, for identity/dedup.")
    result_version: str = Field(default=EXTRACTION_RESULT_VERSION, description="ExtractionResult schema version.")
