from io import BytesIO

import pytest
from sqlalchemy import event, select
from test_extraction import make_pdf

from app.database.session import SessionFactory
from app.documents.exceptions import (
    DocumentExtractionConflict,
    DocumentExtractionFailed,
    DocumentNotFound,
    DocumentStorageUnavailable,
)
from app.documents.extraction import PdfTextExtractor
from app.documents.models import Document, DocumentPage
from app.documents.services.documents import DocumentService
from app.documents.services.extraction import DocumentExtractionService
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage


def create_upload(storage):
    with SessionFactory() as session:
        return (
            DocumentService(session, storage)
            .upload(
                title="Test", filename="test.pdf", source=BytesIO(make_pdf("Some text"))
            )
            .id
        )


@pytest.mark.parametrize("limits", [{"max_pages": 1}, {"max_characters": 4}])
def test_extractor_rejects_processing_limits(limits):
    with pytest.raises(DocumentExtractionFailed, match="extraction_limit_exceeded"):
        PdfTextExtractor(**limits).extract(BytesIO(make_pdf("First", "Second")))


def test_missing_file_does_not_mark_pdf_invalid(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    identifier = create_upload(storage)
    storage.delete(identifier)
    with SessionFactory() as session:
        service = DocumentExtractionService(session, storage, PdfTextExtractor())
        with pytest.raises(DocumentStorageUnavailable):
            service.extract(identifier)
    with SessionFactory() as observer:
        document = observer.get(Document, identifier)
        assert document.status == DocumentStatus.UPLOADED
        assert document.extraction_error is None


def test_sql_failure_rolls_back_pages_and_status(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    identifier = create_upload(storage)

    def reject_pages(session, flush_context, instances):
        if any(isinstance(item, DocumentPage) for item in session.new):
            raise RuntimeError("page write failed")

    with SessionFactory() as session:
        service = DocumentExtractionService(session, storage, PdfTextExtractor())
        event.listen(session, "before_flush", reject_pages)
        try:
            with pytest.raises(RuntimeError, match="page write failed"):
                service.extract(identifier)
        finally:
            event.remove(session, "before_flush", reject_pages)
        assert not session.in_transaction()
        with SessionFactory() as observer:
            assert observer.get(Document, identifier).status == DocumentStatus.UPLOADED
            assert observer.scalars(select(DocumentPage)).all() == []
        assert service.extract(identifier).status == DocumentStatus.EXTRACTED


@pytest.mark.parametrize("complete_delete", [False, True])
def test_deletion_during_parsing_prevents_publication(tmp_path, complete_delete):
    storage = LocalDocumentStorage(tmp_path)
    identifier = create_upload(storage)

    class DeleteWhileExtracting(PdfTextExtractor):
        def extract(self, source):
            pages = super().extract(source)
            with SessionFactory() as other:
                if complete_delete:
                    DocumentService(other, storage).delete(identifier)
                else:
                    with other.begin():
                        other.get(Document, identifier).status = DocumentStatus.DELETING
            return pages

    with SessionFactory() as session:
        service = DocumentExtractionService(session, storage, DeleteWhileExtracting())
        expected = DocumentNotFound if complete_delete else DocumentExtractionConflict
        with pytest.raises(expected):
            service.extract(identifier)
    with SessionFactory() as observer:
        assert observer.scalars(select(DocumentPage)).all() == []


def test_failed_extraction_can_succeed_with_higher_limit(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    identifier = create_upload(storage)
    with SessionFactory() as session:
        limited = DocumentExtractionService(
            session, storage, PdfTextExtractor(max_characters=1)
        )
        with pytest.raises(DocumentExtractionFailed):
            limited.extract(identifier)
        service = DocumentExtractionService(session, storage, PdfTextExtractor())
        document = service.extract(identifier)
        assert document.status == DocumentStatus.EXTRACTED
        assert document.extraction_error is None


def test_normalization_preserves_lines_and_removes_nulls():
    pages = PdfTextExtractor().extract(BytesIO(make_pdf(r"Hello   \r\nworld\000")))
    assert pages[0].text == "Hello\nworld"
