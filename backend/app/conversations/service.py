from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.embeddings import DIMENSIONS, MODEL
from app.conversations.exceptions import ConversationNotFound
from app.conversations.models import Conversation, ConversationMessage
from app.conversations.repository import ConversationRepository
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.repository import DocumentRepository
from app.documents.schemas.answers import AnswerSourceRead
from app.documents.services.answers import DocumentAnswerService
from app.documents.status import DocumentStatus


class ConversationService:
    def __init__(self, session: Session, answers: DocumentAnswerService) -> None:
        self._session = session
        self._repository = ConversationRepository(session)
        self._documents = DocumentRepository(session)
        self._answers = answers

    def _ensure_indexed(self, document_id: UUID) -> None:
        document = self._documents.get_for_update(document_id)
        if document is None:
            raise DocumentNotFound(document_id)
        if (
            document.status != DocumentStatus.INDEXED
            or document.embedding_model != MODEL
            or document.embedding_dimensions != DIMENSIONS
        ):
            raise DocumentSearchConflict

    def _get(self, conversation_id: UUID, *, lock: bool = False) -> Conversation:
        conversation = self._repository.get(conversation_id, lock=lock)
        if conversation is None:
            raise ConversationNotFound(conversation_id)
        return conversation

    def create(self, document_id: UUID) -> Conversation:
        with self._session.begin():
            self._ensure_indexed(document_id)
            conversation = Conversation(document_id=document_id)
            self._repository.add(conversation)
        return conversation

    def get(self, conversation_id: UUID) -> Conversation:
        with self._session.begin():
            return self._get(conversation_id)

    def list(
        self, document_id: UUID, *, limit: int, offset: int
    ) -> Sequence[Conversation]:
        with self._session.begin():
            return self._repository.list(document_id, limit=limit, offset=offset)

    def list_messages(
        self, conversation_id: UUID, *, limit: int, offset: int
    ) -> Sequence[ConversationMessage]:
        with self._session.begin():
            self._get(conversation_id)
            return self._repository.list_messages(
                conversation_id, limit=limit, offset=offset
            )

    def ask(self, conversation_id: UUID, *, question: str) -> ConversationMessage:
        with self._session.begin():
            document_id = self._get(conversation_id).document_id
        # Aucun historique envoyé au LLM ; aucun verrou conservé pendant Gemini.
        answer = self._answers.ask(document_id, question=question)
        sources = [
            AnswerSourceRead.model_validate(source).model_dump(mode="json")
            for source in answer.sources
        ]
        with self._session.begin():
            # Même ordre de verrouillage : document puis conversation. Le second
            # sérialise l'attribution de séquence entre publications concurrentes.
            self._ensure_indexed(document_id)
            self._get(conversation_id, lock=True)
            message = ConversationMessage(
                conversation_id=conversation_id,
                sequence=self._repository.next_sequence(conversation_id),
                question=question,
                answer=answer.answer,
                abstained=answer.abstained,
                sources=sources,
            )
            self._repository.add_message(message)
        return message
