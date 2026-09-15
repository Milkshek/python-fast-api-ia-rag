from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.documents.exceptions import DocumentNotFound
from app.documents.models import Document
from app.documents.repository import DocumentRepository


class DocumentService:
    """Cas d'usage indépendants de HTTP, avec une transaction par opération."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = DocumentRepository(session)

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

    def delete(self, document_id: UUID) -> None:
        with self._session.begin():
            document = self._require_document(document_id)
            self._repository.delete(document)

    def _require_document(self, document_id: UUID) -> Document:
        document = self._repository.get(document_id)
        if document is None:
            raise DocumentNotFound(document_id)
        return document
