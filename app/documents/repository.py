from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.models import Document


class DocumentRepository:
    """Accès aux documents ; la transaction appartient à l'appelant."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(document)

    def get(self, document_id: UUID) -> Document | None:
        return self._session.get(Document, document_id)

    def list(self, *, limit: int, offset: int) -> Sequence[Document]:
        statement = (
            select(Document)
            .order_by(Document.created_at, Document.id)
            .offset(offset)
            .limit(limit)
        )
        return self._session.scalars(statement).all()

    def delete(self, document: Document) -> None:
        self._session.delete(document)
