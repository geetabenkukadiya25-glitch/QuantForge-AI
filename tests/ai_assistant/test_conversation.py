"""Tests for `ConversationManager`/`ConversationSession`."""

from app.ai_assistant.conversation import ConversationManager
from tests.ai_assistant.conftest import make_context


def test_start_creates_empty_session():
    session = ConversationManager().start()
    assert session.turns == ()
    assert session.session_id


def test_ask_appends_a_turn_on_success(full_context):
    manager = ConversationManager()
    session = manager.start()
    context = make_context(full_context, "Explain optimization")
    session, assistant_session = manager.ask(session, context)
    assert assistant_session.is_successful
    assert len(session.turns) == 1
    assert session.turns[0].query == "Explain optimization"


def test_ask_does_not_append_turn_on_failure(full_context):
    manager = ConversationManager()
    session = manager.start()
    context = make_context(full_context, "")
    session, assistant_session = manager.ask(session, context)
    assert not assistant_session.is_successful
    assert session.turns == ()


def test_multiple_turns_accumulate_in_order(full_context):
    manager = ConversationManager()
    session = manager.start()
    session, _ = manager.ask(session, make_context(full_context, "Explain optimization"))
    session, _ = manager.ask(session, make_context(full_context, "Explain validation"))
    assert [t.query for t in session.turns] == ["Explain optimization", "Explain validation"]
    assert [t.turn_index for t in session.turns] == [0, 1]


def test_append_returns_new_session_never_mutates(full_context):
    manager = ConversationManager()
    original = manager.start()
    updated, _ = manager.ask(original, make_context(full_context, "Explain replay"))
    assert original.turns == ()
    assert len(updated.turns) == 1
    assert original is not updated


def test_turn_carries_result_id(full_context):
    manager = ConversationManager()
    session = manager.start()
    session, assistant_session = manager.ask(session, make_context(full_context, "Explain optimization"))
    assert session.turns[0].result_id == assistant_session.result.result_id


def test_one_turn_does_not_influence_the_next(full_context):
    """Each turn is answered independently -- asking an unrelated question second
    must not be biased by the first turn's intent/results."""
    manager = ConversationManager()
    session = manager.start()
    session, first = manager.ask(session, make_context(full_context, "Explain optimization"))
    session, second = manager.ask(session, make_context(full_context, "Explain replay"))
    assert first.result.answer.intent != second.result.answer.intent
    assert second.result.answer.intent.value == "EXPLAIN_REPLAY"
