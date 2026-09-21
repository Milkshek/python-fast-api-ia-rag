from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.documents.status import DocumentStatus


class DocumentCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    filename: str = Field(min_length=1, max_length=255)


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    created_at: datetime
    status: DocumentStatus
    size_bytes: int | None
    extraction_error: str | None
    embedding_model: str | None
    embedding_dimensions: int | None


class DocumentPageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: UUID
    page_number: int
    text: str


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    page_number: int
    start_offset: int
    end_offset: int
    text: str


class DocumentSearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10, strict=True)


class DocumentSearchHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk: DocumentChunkRead
    score: float


class DocumentQuestion(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=1, max_length=2000)


class AnswerSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chunk: DocumentChunkRead


class DocumentAnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer: str
    abstained: bool
    sources: list[AnswerSourceRead]
