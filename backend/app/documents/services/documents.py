import logging
from collections.abc import Sequence
from pathlib import Path
from typing import BinaryIO
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.documents.exceptions import (
    DocumentContentConflict,
    DocumentNotFound,
    DocumentPageNotFound,
    DocumentStorageUnavailable,
    EmptyDocumentFile,
    UnsupportedDocumentFile,
)
from app.documents.models import Document, DocumentPage
from app.documents.repository import DocumentRepository
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage

logger = logging.getLogger(__name__)


class DocumentService:
    """Cas d'usage et transactions ; compensation entre SQL et stockage local."""

    def __init__(self, session: Session, storage: LocalDocumentStorage) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._storage = storage

    def upload(self, *, title: str, filename: str, source: BinaryIO) -> Document:
        self._validate_pdf(filename, source)
        document_id = uuid4()
        size = self._storage.save(document_id, source)
        document = Document(
            id=document_id,
            title=title,
            filename=filename,
            status=DocumentStatus.UPLOADED,
            size_bytes=size,
        )
        self._persist_uploaded_document(document)
        return document

    def create(self, *, title: str, filename: str) -> Document:
        with self._session.begin():
            document = Document(title=title, filename=filename)
            self._repository.add(document)
        return document

    def list(self, *, limit: int, offset: int) -> Sequence[Document]:
        with self._session.begin():
            return self._repository.list(limit=limit, offset=offset)

    def get(self, document_id: UUID) -> Document:
        with self._session.begin():
            return self._require_document(document_id)

    def file_path(self, document_id: UUID) -> Path:
        with self._session.begin():
            document = self._require_document(document_id)
            if document.status in (
                DocumentStatus.METADATA_ONLY,
                DocumentStatus.DELETING,
            ):
                raise DocumentContentConflict
        # Aucune transaction SQL pendant le contrôle disque ou le transfert HTTP.
        return self._storage.file_path(document_id)

    def get_page(self, document_id: UUID, page_number: int) -> DocumentPage:
        with self._session.begin():
            document = self._require_document(document_id)
            if document.status == DocumentStatus.DELETING:
                raise DocumentContentConflict
            page = self._repository.get_page(document_id, page_number)
            if page is None:
                raise DocumentPageNotFound
            return page

    def delete(self, document_id: UUID) -> None:
        with self._session.begin():
            document = self._repository.get_for_update(document_id)
            if document is None:
                raise DocumentNotFound(document_id)
            if document.status == DocumentStatus.METADATA_ONLY:
                self._repository.delete(document)
                return
            document.status = DocumentStatus.DELETING
        # Le statut reste DELETING si le disque échoue : DELETE peut être rejoué.
        self._storage.delete(document_id)
        with self._session.begin():
            document = self._repository.get_for_update(document_id)
            if document is not None:
                self._repository.delete(document)

    def _validate_pdf(self, filename: str, source: BinaryIO) -> None:
        if Path(filename).suffix.lower() != ".pdf":
            raise UnsupportedDocumentFile
        header = source.read(5)
        if not header:
            raise EmptyDocumentFile
        if header != b"%PDF-":
            raise UnsupportedDocumentFile
        source.seek(0)

    def _persist_uploaded_document(self, document: Document) -> None:
        document_id = document.id
        commit_started = False
        try:
            with self._session.begin():
                self._repository.add(document)
                self._session.flush()
                commit_started = True
        except Exception:
            if commit_started:
                # La base a pu valider sans que sa confirmation nous parvienne.
                logger.exception(
                    "Upload commit uncertain; retaining file %s", document_id
                )
            else:
                self._compensate_upload(document_id)
            raise

    def _compensate_upload(self, document_id: UUID) -> None:
        try:
            self._storage.delete(document_id)
        except DocumentStorageUnavailable:
            logger.exception("Unable to compensate upload %s", document_id)

    def _require_document(self, document_id: UUID) -> Document:
        document = self._repository.get(document_id)
        if document is None:
            raise DocumentNotFound(document_id)
        return document
