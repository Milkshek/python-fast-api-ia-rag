from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.conversations.models import Conversation, ConversationMessage


class ConversationRepository:
    """Requêtes SQL ; le service possède les transactions."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, conversation: Conversation) -> None:
        self._session.add(conversation)

    def get(self, conversation_id: UUID, *, lock: bool = False) -> Conversation | None:
        statement = select(Conversation).where(Conversation.id == conversation_id)
        if lock:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return self._session.scalar(statement)

    def list(
        self, document_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Conversation]:
        return self._session.scalars(
            select(Conversation)
            .where(Conversation.document_id == document_id)
            .order_by(Conversation.created_at.desc(), Conversation.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()

    def list_messages(
        self, conversation_id: UUID, *, limit: int, offset: int
    ) -> Sequence[ConversationMessage]:
        return self._session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.sequence)
            .limit(limit)
            .offset(offset)
        ).all()

    def next_sequence(self, conversation_id: UUID) -> int:
        latest = self._session.scalar(
            select(func.max(ConversationMessage.sequence)).where(
                ConversationMessage.conversation_id == conversation_id
            )
        )
        return (latest or 0) + 1

    def add_message(self, message: ConversationMessage) -> None:
        self._session.add(message)
