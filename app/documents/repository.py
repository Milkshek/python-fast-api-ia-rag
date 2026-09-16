from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.documents.models import Document, DocumentPage


class DocumentRepository:
    """Accès aux documents ; la transaction appartient à l'appelant."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(document)

    def get(self, document_id: UUID) -> Document | None:
        return self._session.get(Document, document_id)

    def get_for_update(self, document_id: UUID) -> Document | None:
        return self._session.scalar(
            select(Document)
            .where(Document.id == document_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

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

    def replace_pages(self, document_id: UUID, pages: Sequence[DocumentPage]) -> None:
        self._session.execute(
            delete(DocumentPage).where(DocumentPage.document_id == document_id)
        )
        self._session.add_all(pages)

    def list_pages(
        self, document_id: UUID, *, limit: int, offset: int
    ) -> Sequence[DocumentPage]:
        return self._session.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_number)
            .offset(offset)
            .limit(limit)
        ).all()
