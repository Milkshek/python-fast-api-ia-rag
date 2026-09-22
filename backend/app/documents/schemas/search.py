from pydantic import BaseModel, ConfigDict, Field

from app.documents.schemas.processing import DocumentChunkRead


class DocumentSearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10, strict=True)


class DocumentSearchHitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk: DocumentChunkRead
    score: float
