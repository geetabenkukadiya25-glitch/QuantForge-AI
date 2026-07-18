"""A stateless-per-turn conversation history over multiple assistant queries.

`ConversationManager` never lets one turn's answer influence how the
next query is classified or searched -- each turn is answered completely
independently by `AssistantRunner`, exactly like every other call in
this module. "Conversation" here means only an ordered, append-only
transcript of past turns, never a memory that biases future reasoning
(no hidden state, no generative context window).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from app.ai_assistant.context import AssistantContext
from app.ai_assistant.models import AssistantResult, QueryIntent
from app.ai_assistant.runner import AssistantRunner, AssistantSession


@dataclass(frozen=True)
class ConversationTurn:
    """One question/answer exchange in a conversation."""

    turn_index: int
    query: str
    intent: QueryIntent
    result_id: str
    asked_at: datetime


@dataclass
class ConversationSession:
    """An append-only transcript of every turn asked in one conversation."""

    session_id: str
    turns: tuple[ConversationTurn, ...] = ()

    def append(self, turn: ConversationTurn) -> "ConversationSession":
        """Return a NEW `ConversationSession` with `turn` appended -- never mutates in place."""
        return ConversationSession(session_id=self.session_id, turns=self.turns + (turn,))


class ConversationManager:
    """Wraps `AssistantRunner` to maintain a running, read-only turn history across multiple queries."""

    def __init__(self, runner: AssistantRunner | None = None) -> None:
        self._runner = runner or AssistantRunner()

    def start(self) -> ConversationSession:
        return ConversationSession(session_id=str(uuid.uuid4()))

    def ask(self, session: ConversationSession, context: AssistantContext) -> tuple[ConversationSession, AssistantSession]:
        """Answer `context.query`, returning the UPDATED conversation session and the raw `AssistantSession`.

        Never raises -- inspect the returned `AssistantSession.is_successful`.
        A failed turn is still recorded in a `ConversationSession`'s history
        only once it succeeds; a failed query does not append a turn.
        """
        assistant_session = self._runner.try_execute(context)
        if not assistant_session.is_successful:
            return session, assistant_session

        result = assistant_session.result
        turn = ConversationTurn(
            turn_index=len(session.turns),
            query=context.query,
            intent=result.answer.intent,
            result_id=result.result_id,
            asked_at=datetime.now(timezone.utc),
        )
        return session.append(turn), assistant_session
