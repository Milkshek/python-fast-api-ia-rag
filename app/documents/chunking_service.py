from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.documents.chunking import TextChunker
from app.documents.exceptions import DocumentChunkingConflict, DocumentNotFound
from app.documents.models import Document, DocumentChunk, DocumentPage
from app.documents.repository import DocumentRepository
from app.documents.status import DocumentStatus


class DocumentChunkingService:
    """Découpage hors transaction puis publication atomique des chunks."""

    def __init__(self, session: Session, chunker: TextChunker) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._chunker = chunker

    def chunk(self, document_id: UUID) -> Document:
        with self._session.begin():
            document = self._require_document(document_id)
            self._ensure_chunkable(document)
            if document.status == DocumentStatus.CHUNKED:
                return document
            pages = self._repository.all_pages(document_id)
        chunks = self._build_chunks(document_id, pages)
        return self._publish_chunks(document_id, chunks)

    def list_chunks(
        self, document_id: UUID, *, limit: int, offset: int
    ) -> Sequence[DocumentChunk]:
        with self._session.begin():
            self._require_document(document_id)
            return self._repository.list_chunks(document_id, limit=limit, offset=offset)

    def _build_chunks(
        self, document_id: UUID, pages: Sequence[DocumentPage]
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page in pages:
            for chunk in self._chunker.split(page.text):
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        chunk_index=len(chunks) + 1,
                        page_number=page.page_number,
                        start_offset=chunk.start_offset,
                        end_offset=chunk.end_offset,
                        text=chunk.text,
                    )
                )
        if not chunks:
            raise DocumentChunkingConflict
        return chunks

    def _publish_chunks(
        self, document_id: UUID, chunks: Sequence[DocumentChunk]
    ) -> Document:
        with self._session.begin():
            document = self._require_document(document_id, lock=True)
            self._ensure_chunkable(document)
            if document.status != DocumentStatus.CHUNKED:
                self._repository.add_chunks(chunks)
                document.status = DocumentStatus.CHUNKED
        return document

    def _require_document(self, document_id: UUID, *, lock: bool = False) -> Document:
        document = (
            self._repository.get_for_update(document_id)
            if lock
            else self._repository.get(document_id)
        )
        if document is None:
            raise DocumentNotFound(document_id)
        return document

    def _ensure_chunkable(self, document: Document) -> None:
        if document.status not in (DocumentStatus.EXTRACTED, DocumentStatus.CHUNKED):
            raise DocumentChunkingConflict
