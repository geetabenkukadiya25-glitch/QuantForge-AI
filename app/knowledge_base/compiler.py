"""Compiles a validated `KnowledgeContext` into an immutable `KnowledgeResult`.

A pure transformation: given a `KnowledgeContext` and its already-computed
`KnowledgeStatistics`, build the final `KnowledgeResult` and its content
checksum -- the same discipline `ResearchCompiler`/`ValidationCompiler`/
`OptimizationCompiler`/`BacktestCompiler` established: every identity/
timestamp field is excluded from the checksum payload before hashing, so
two runs of the same context produce the same checksum.
"""

import uuid
from datetime import datetime, timezone

from app.core.checksums import compute_checksum
from app.knowledge_base.context import KnowledgeContext
from app.knowledge_base.metadata import KNOWLEDGE_RESULT_VERSION, KnowledgeMetadata
from app.knowledge_base.models import KnowledgeEntry, KnowledgeResult, KnowledgeStatistics
from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeCompiler:
    """Builds a `KnowledgeResult` from one build's validated entries and computed statistics."""

    def compile(self, context: KnowledgeContext, statistics: KnowledgeStatistics) -> KnowledgeResult:
        # Sorted by entry_id (not `context.entries`' input order) so the
        # checksum -- and the compiled result -- stay independent of the
        # order entries were supplied in.
        ordered_entries = tuple(sorted(context.entries, key=lambda e: e.entry_id))

        metadata = KnowledgeMetadata(
            knowledge_id=str(uuid.uuid4()),
            entry_count=len(ordered_entries),
            category_count=statistics.total_categories,
            result_version=KNOWLEDGE_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, ordered_entries, statistics)

        result = KnowledgeResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            entries=ordered_entries,
            statistics=statistics,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled knowledge base build (%d entries, checksum=%s)", len(ordered_entries), checksum[:12])
        return result

    @staticmethod
    def _checksum(metadata: KnowledgeMetadata, configuration, entries: tuple[KnowledgeEntry, ...], statistics: KnowledgeStatistics) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.knowledge_id`) -- two runs of
        the same context produce the same checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["knowledge_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "entries": [e.model_dump(mode="json") for e in entries],
            "statistics": statistics.model_dump(mode="json"),
        }
        return compute_checksum(payload)
