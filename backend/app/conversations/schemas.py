from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.documents.schemas.answers import AnswerSourceRead


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: UUID


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    created_at: datetime


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    sequence: int
    question: str
    answer: str
    abstained: bool
    sources: list[AnswerSourceRead]
    created_at: datetime
