"""Compiles a completed query/answer into an immutable `AssistantResult`.

A pure transformation: given an `AssistantContext` and its already-
composed `AssistantAnswer`, build the final `AssistantResult` and its
content checksum -- the same discipline every prior compiler in this
platform established: every identity/timestamp field is excluded from
the checksum payload before hashing, so two answers to the same query
against the same registered data produce the same checksum. Uses the
shared `app.core.checksums` helper, the same canonicalization every
other engine's compiler delegates to.
"""

import uuid
from datetime import datetime, timezone

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.metadata import AI_ASSISTANT_RESULT_VERSION, AssistantMetadata
from app.ai_assistant.models import AssistantAnswer, AssistantResult
from app.core.checksums import compute_checksum, sha256_hex
from app.utils.logger import get_logger

logger = get_logger(__name__)


class AssistantCompiler:
    """Builds an `AssistantResult` from one query's context and composed answer."""

    def compile(self, context: AssistantContext, answer: AssistantAnswer) -> AssistantResult:
        metadata = AssistantMetadata(
            assistant_id=str(uuid.uuid4()),
            query_checksum=sha256_hex(context.query),
            intent=answer.intent.value,
            result_version=AI_ASSISTANT_RESULT_VERSION,
        )

        checksum = self._checksum(metadata, context.configuration, answer)

        result = AssistantResult(
            result_id=str(uuid.uuid4()),
            metadata=metadata,
            configuration=context.configuration,
            answer=answer,
            checksum=checksum,
            built_at=datetime.now(timezone.utc),
        )

        logger.info("Compiled assistant answer for intent '%s' (checksum=%s)", answer.intent.value, checksum[:12])
        return result

    @staticmethod
    def _checksum(metadata: AssistantMetadata, configuration, answer: AssistantAnswer) -> str:
        """A content hash over everything except identity/timestamp fields
        (`result_id`, `built_at`, `metadata.assistant_id`) -- two answers to
        the same query against the same registered data produce the same
        checksum, verifying determinism.
        """
        metadata_payload = metadata.model_dump(mode="json")
        del metadata_payload["assistant_id"]
        payload = {
            "metadata": metadata_payload,
            "configuration": configuration.model_dump(mode="json"),
            "answer": answer.model_dump(mode="json"),
        }
        return compute_checksum(payload)
