from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from test_extraction import make_pdf

from app.database.session import SessionFactory
from app.documents.chunking import TextChunker
from app.documents.exceptions import DocumentChunkingConflict, DocumentNotFound
from app.documents.extraction import PdfTextExtractor
from app.documents.models import Document, DocumentChunk
from app.documents.services.chunking import DocumentChunkingService
from app.documents.services.documents import DocumentService
from app.documents.services.extraction import DocumentExtractionService
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage
from app.main import app


def extracted_document(storage):
    with SessionFactory() as session:
        identifier = (
            DocumentService(session, storage)
            .upload(
                title="Chunks",
                filename="chunks.pdf",
                source=BytesIO(make_pdf("Some text")),
            )
            .id
        )
        DocumentExtractionService(session, storage, PdfTextExtractor()).extract(
            identifier
        )
        return identifier


def test_chunk_write_failure_rolls_back_status_and_all_chunks(tmp_path):
    storage = LocalDocumentStorage(tmp_path)
    identifier = extracted_document(storage)

    def reject_chunks(session, flush_context, instances):
        if any(isinstance(item, DocumentChunk) for item in session.new):
            raise RuntimeError("chunk write failed")

    with SessionFactory() as session:
        service = DocumentChunkingService(session, TextChunker(chunk_size=4, overlap=1))
        event.listen(session, "before_flush", reject_chunks)
        try:
            with pytest.raises(RuntimeError, match="chunk write failed"):
                service.chunk(identifier)
        finally:
            event.remove(session, "before_flush", reject_chunks)
        with SessionFactory() as observer:
            assert observer.get(Document, identifier).status == DocumentStatus.EXTRACTED
            assert observer.scalars(select(DocumentChunk)).all() == []
        assert service.chunk(identifier).status == DocumentStatus.CHUNKED


@pytest.mark.parametrize("delete_completely", [False, True])
def test_deletion_during_chunking_prevents_publication(tmp_path, delete_completely):
    storage = LocalDocumentStorage(tmp_path)
    identifier = extracted_document(storage)

    class DeleteWhileSplitting(TextChunker):
        def split(self, content):
            with SessionFactory() as other:
                if delete_completely:
                    DocumentService(other, storage).delete(identifier)
                else:
                    with other.begin():
                        other.get(Document, identifier).status = DocumentStatus.DELETING
            return super().split(content)

    with SessionFactory() as session:
        service = DocumentChunkingService(session, DeleteWhileSplitting())
        error = DocumentNotFound if delete_completely else DocumentChunkingConflict
        with pytest.raises(error):
            service.chunk(identifier)
    with SessionFactory() as observer:
        assert observer.scalars(select(DocumentChunk)).all() == []


def test_concurrent_publication_keeps_first_chunks(tmp_path):
    identifier = extracted_document(LocalDocumentStorage(tmp_path))
    published = []

    class PublishWhileSplitting(TextChunker):
        def split(self, content):
            with SessionFactory() as other:
                service = DocumentChunkingService(other, TextChunker())
                service.chunk(identifier)
                published.extend(
                    c.id for c in service.list_chunks(identifier, limit=20, offset=0)
                )
            return super().split(content)

    with SessionFactory() as session:
        service = DocumentChunkingService(session, PublishWhileSplitting())
        assert service.chunk(identifier).status == DocumentStatus.CHUNKED
        assert [
            c.id for c in service.list_chunks(identifier, limit=20, offset=0)
        ] == published


def test_chunking_http_errors_and_pagination_validation():
    with TestClient(app) as client:
        url = f"/documents/{uuid4()}"
        assert client.post(f"{url}/chunk").status_code == 404
        assert client.get(f"{url}/chunks").status_code == 404
        assert client.get(f"{url}/chunks?limit=0").status_code == 422
        assert client.get(f"{url}/chunks?offset=-1").status_code == 422
        document = client.post(
            "/documents", json={"title": "Metadata", "filename": "a.pdf"}
        ).json()
        assert client.post(f"/documents/{document['id']}/chunk").status_code == 409
