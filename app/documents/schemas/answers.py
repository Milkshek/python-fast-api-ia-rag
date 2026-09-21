from pydantic import BaseModel, ConfigDict, Field

from app.documents.schemas.processing import DocumentChunkRead


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
