from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
