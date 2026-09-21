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
