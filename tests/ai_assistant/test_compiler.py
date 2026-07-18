"""Tests for `AssistantCompiler`."""

from app.ai_assistant.runner import AssistantRunner
from tests.ai_assistant.conftest import make_context


def test_compile_produces_valid_checksum(full_context):
    context = make_context(full_context, "Explain optimization")
    result = AssistantRunner().execute(context)
    assert len(result.checksum) == 64
    assert all(c in "0123456789abcdef" for c in result.checksum)


def test_compile_is_deterministic_for_same_query(full_context):
    context = make_context(full_context, "Explain optimization")
    result_1 = AssistantRunner().execute(context)
    result_2 = AssistantRunner().execute(context)
    assert result_1.checksum == result_2.checksum


def test_compile_checksum_excludes_identity_fields(full_context):
    context = make_context(full_context, "Explain optimization")
    result_1 = AssistantRunner().execute(context)
    result_2 = AssistantRunner().execute(context)
    assert result_1.result_id != result_2.result_id
    assert result_1.metadata.assistant_id != result_2.metadata.assistant_id
    assert result_1.checksum == result_2.checksum


def test_compile_query_checksum_is_sha256_of_query(full_context):
    from app.core.checksums import sha256_hex

    context = make_context(full_context, "Explain validation")
    result = AssistantRunner().execute(context)
    assert result.metadata.query_checksum == sha256_hex("Explain validation")


def test_compile_different_queries_produce_different_checksums(full_context):
    context_a = make_context(full_context, "Explain optimization")
    context_b = make_context(full_context, "Explain validation")
    result_a = AssistantRunner().execute(context_a)
    result_b = AssistantRunner().execute(context_b)
    assert result_a.checksum != result_b.checksum


def test_compile_metadata_intent_matches_answer_intent(full_context):
    context = make_context(full_context, "Explain replay")
    result = AssistantRunner().execute(context)
    assert result.metadata.intent == result.answer.intent.value
