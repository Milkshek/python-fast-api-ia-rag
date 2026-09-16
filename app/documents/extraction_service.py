from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.documents.exceptions import (
    DocumentExtractionConflict,
    DocumentExtractionFailed,
    DocumentNotFound,
)
from app.documents.extraction import PdfTextExtractor
from app.documents.models import Document, DocumentPage
from app.documents.repository import DocumentRepository
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage


class DocumentExtractionService:
    """Extraction hors transaction puis publication atomique des pages."""

    def __init__(
        self,
        session: Session,
        storage: LocalDocumentStorage,
        extractor: PdfTextExtractor,
    ) -> None:
        self._session = session
        self._storage = storage
        self._extractor = extractor
        self._repository = DocumentRepository(session)

    def extract(self, document_id: UUID) -> Document:
        with self._session.begin():
            document = self._require_document(document_id)
            self._ensure_extractable(document)
            if document.status in (DocumentStatus.EXTRACTED, DocumentStatus.CHUNKED):
                return document
        try:
            with self._storage.open(document_id) as source:
                pages = self._extractor.extract(source)
        except DocumentExtractionFailed as error:
            self._record_failure(document_id, error.code)
            raise
        with self._session.begin():
            document = self._require_document(document_id, lock=True)
            self._ensure_extractable(document)
            if document.status not in (
                DocumentStatus.EXTRACTED,
                DocumentStatus.CHUNKED,
            ):
                self._repository.replace_pages(
                    document_id,
                    [
                        DocumentPage(
                            document_id=document_id,
                            page_number=page.page_number,
                            text=page.text,
                        )
                        for page in pages
                    ],
                )
                document.status = DocumentStatus.EXTRACTED
                document.extraction_error = None
        return document

    def list_pages(
        self, document_id: UUID, *, limit: int, offset: int
    ) -> Sequence[DocumentPage]:
        with self._session.begin():
            self._require_document(document_id)
            return self._repository.list_pages(document_id, limit=limit, offset=offset)

    def _record_failure(self, document_id: UUID, code: str) -> None:
        with self._session.begin():
            document = self._require_document(document_id, lock=True)
            self._ensure_extractable(document)
            # Une autre requête a pu publier des pages pendant notre parsing.
            if document.status not in (
                DocumentStatus.EXTRACTED,
                DocumentStatus.CHUNKED,
            ):
                document.status = DocumentStatus.FAILED
                document.extraction_error = code

    def _require_document(self, document_id: UUID, *, lock: bool = False) -> Document:
        document = (
            self._repository.get_for_update(document_id)
            if lock
            else self._repository.get(document_id)
        )
        if document is None:
            raise DocumentNotFound(document_id)
        return document

    def _ensure_extractable(self, document: Document) -> None:
        if document.status in (DocumentStatus.METADATA_ONLY, DocumentStatus.DELETING):
            raise DocumentExtractionConflict
