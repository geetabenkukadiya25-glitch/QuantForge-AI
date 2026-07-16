"""YouTube transcript reader (placeholder).

Will fetch and clean video transcripts as raw text input for the AI
strategy extractor.
"""

from app.core.exceptions import NotImplementedYetError


class TranscriptReader:
    """Retrieves transcripts for a given YouTube video."""

    def read(self, video_url: str) -> str:
        """Not implemented until Phase 2 (YouTube Strategy Import)."""
        raise NotImplementedYetError(
            "TranscriptReader.read", phase="Phase 2 (YouTube Strategy Import)"
        )
