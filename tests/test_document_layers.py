from uuid import uuid4

import pytest

from app.database.session import SessionFactory
from app.documents.exceptions import DocumentNotFound
from app.documents.models import Document
from app.documents.repository import DocumentRepository
from app.documents.service import DocumentService
from app.documents.storage import LocalDocumentStorage


def test_repository_does_not_commit():
    with SessionFactory() as session:
        repository = DocumentRepository(session)
        document = Document(title="Non validé", filename="a.pdf")
        repository.add(document)
        session.flush()
        identifier = document.id
        with SessionFactory() as observer:
            assert observer.get(Document, identifier) is None
        session.rollback()


def test_service_commits_without_http(tmp_path):
    with SessionFactory() as session:
        service = DocumentService(session, LocalDocumentStorage(tmp_path))
        document = service.create(title="Persisté", filename="a.pdf")
        with SessionFactory() as observer:
            stored = observer.get(Document, document.id)
            assert stored is not None
            assert stored.title == "Persisté"
        assert service.get(document.id).id == document.id
        service.delete(document.id)
        with SessionFactory() as observer:
            assert observer.get(Document, document.id) is None


def test_service_missing_document_leaves_session_usable(tmp_path):
    with SessionFactory() as session:
        service = DocumentService(session, LocalDocumentStorage(tmp_path))
        with pytest.raises(DocumentNotFound):
            service.delete(uuid4())
        assert not session.in_transaction()
        assert service.create(title="Après erreur", filename="a.pdf").id
