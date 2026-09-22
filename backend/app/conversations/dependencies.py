from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.conversations.service import ConversationService
from app.database.session import get_session
from app.documents.dependencies import get_document_answer_service
from app.documents.services.answers import DocumentAnswerService


def get_conversation_service(
    session: Annotated[Session, Depends(get_session)],
    answers: Annotated[DocumentAnswerService, Depends(get_document_answer_service)],
) -> ConversationService:
    return ConversationService(session, answers)
