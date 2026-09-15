from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import event, select

from app.database.session import SessionFactory
from app.documents.exceptions import DocumentStorageUnavailable
from app.documents.models import Document
from app.documents.service import DocumentService
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage

PDF = b"%PDF-1.4\nexample\n%%EOF\n"


def test_uncertain_commit_keeps_file_for_persisted_document(tmp_path):
    def lose_confirmation(session):
        raise RuntimeError("commit confirmation lost")

    with SessionFactory() as session:
        service = DocumentService(session, LocalDocumentStorage(tmp_path))
        event.listen(session, "after_commit", lose_confirmation)
        try:
            with pytest.raises(RuntimeError, match="commit confirmation lost"):
                service.upload(title="A", filename="a.pdf", source=BytesIO(PDF))
        finally:
            event.remove(session, "after_commit", lose_confirmation)
    with SessionFactory() as observer:
        document = observer.scalar(select(Document))
        assert document is not None
        assert (tmp_path / f"{document.id}.pdf").read_bytes() == PDF


def test_metadata_delete_does_not_access_storage(tmp_path, monkeypatch):
    storage = LocalDocumentStorage(tmp_path)

    def unavailable(document_id):
        raise DocumentStorageUnavailable

    monkeypatch.setattr(storage, "delete", unavailable)
    with SessionFactory() as session:
        service = DocumentService(session, storage)
        document = service.create(title="Métadonnées", filename="a.pdf")
        service.delete(document.id)
        with SessionFactory() as observer:
            assert observer.get(Document, document.id) is None


def test_interrupted_copy_removes_partial_file(tmp_path):
    class BrokenStream(BytesIO):
        def read(self, size=-1):
            if self.tell() > 0:
                raise OSError("simulated interruption")
            return super().read(8)

    storage = LocalDocumentStorage(tmp_path)
    with pytest.raises(DocumentStorageUnavailable):
        storage.save(uuid4(), BrokenStream(PDF))
    assert list(tmp_path.iterdir()) == []


def test_failed_upload_flush_removes_saved_file(tmp_path):
    def fail_flush(session, flush_context, instances):
        raise RuntimeError("simulated flush failure")

    with SessionFactory() as session:
        service = DocumentService(session, LocalDocumentStorage(tmp_path))
        event.listen(session, "before_flush", fail_flush)
        try:
            with pytest.raises(RuntimeError, match="simulated flush failure"):
                service.upload(title="A", filename="a.pdf", source=BytesIO(PDF))
        finally:
            event.remove(session, "before_flush", fail_flush)
        assert not session.in_transaction()
    assert list(tmp_path.iterdir()) == []
    with SessionFactory() as observer:
        assert observer.scalars(select(Document)).all() == []


def test_failed_file_deletion_can_be_retried(tmp_path, monkeypatch):
    storage = LocalDocumentStorage(tmp_path)
    with SessionFactory() as session:
        service = DocumentService(session, storage)
        document = service.upload(title="A", filename="a.pdf", source=BytesIO(PDF))
        original_delete = storage.delete

        def fail_delete(document_id):
            raise DocumentStorageUnavailable

        monkeypatch.setattr(storage, "delete", fail_delete)
        with pytest.raises(DocumentStorageUnavailable):
            service.delete(document.id)
        with SessionFactory() as observer:
            persisted = observer.get(Document, document.id)
            assert persisted is not None
            assert persisted.status == DocumentStatus.DELETING
        assert (tmp_path / f"{document.id}.pdf").exists()
        monkeypatch.setattr(storage, "delete", original_delete)
        service.delete(document.id)
        with SessionFactory() as observer:
            assert observer.get(Document, document.id) is None
    assert list(tmp_path.iterdir()) == []


def test_failed_final_delete_commit_can_be_retried_without_file(tmp_path):
    commits = 0

    def fail_second_commit(session):
        nonlocal commits
        commits += 1
        if commits == 2:
            raise RuntimeError("simulated final commit failure")

    with SessionFactory() as session:
        service = DocumentService(session, LocalDocumentStorage(tmp_path))
        document = service.upload(title="A", filename="a.pdf", source=BytesIO(PDF))
        identifier = document.id
        event.listen(session, "before_commit", fail_second_commit)
        try:
            with pytest.raises(RuntimeError, match="simulated final commit failure"):
                service.delete(identifier)
        finally:
            event.remove(session, "before_commit", fail_second_commit)
        assert list(tmp_path.iterdir()) == []
        with SessionFactory() as observer:
            persisted = observer.get(Document, identifier)
            assert persisted is not None
            assert persisted.status == DocumentStatus.DELETING
        service.delete(identifier)
        with SessionFactory() as observer:
            assert observer.get(Document, identifier) is None
