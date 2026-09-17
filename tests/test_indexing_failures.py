import pytest
from sqlalchemy import event, select
from test_chunking_failures import extracted_document

from app.ai.embeddings import DIMENSIONS, EmbeddingQuotaExceeded, GeminiEmbeddingClient
from app.database.session import SessionFactory
from app.documents.chunking import TextChunker
from app.documents.chunking_service import DocumentChunkingService
from app.documents.exceptions import DocumentIndexingConflict, DocumentNotFound
from app.documents.indexing_service import DocumentIndexingService
from app.documents.models import ChunkEmbedding, Document
from app.documents.service import DocumentService
from app.documents.status import DocumentStatus
from app.documents.storage import LocalDocumentStorage


class StubEmbeddings(GeminiEmbeddingClient):
    def __init__(self, action=lambda: None):
        self.action = action
        self.calls = 0

    def embed_documents(self, texts):
        self.calls += 1
        self.action()
        return [[1.0] + [0.0] * (DIMENSIONS - 1) for text in texts]


def chunked_document(storage):
    identifier = extracted_document(storage)
    with SessionFactory() as session:
        DocumentChunkingService(session, TextChunker()).chunk(identifier)
    return identifier


@pytest.mark.parametrize("previous_index", [False, True])
def test_sql_failure_preserves_previous_index_or_chunked_state(
    tmp_path, previous_index
):
    identifier = chunked_document(LocalDocumentStorage(tmp_path))
    with SessionFactory() as session:
        service = DocumentIndexingService(session, StubEmbeddings())
        if previous_index:
            service.index(identifier)
        with SessionFactory() as observer:
            previous_generation = observer.get(
                Document, identifier
            ).embedding_generation

        def fail_write(session, flush_context, instances):
            if any(isinstance(obj, ChunkEmbedding) for obj in session.new):
                raise RuntimeError("embedding write failure")

        event.listen(session, "before_flush", fail_write)
        try:
            with pytest.raises(RuntimeError, match="embedding write failure"):
                service.index(identifier, force=True)
        finally:
            event.remove(session, "before_flush", fail_write)
        with SessionFactory() as observer:
            document = observer.get(Document, identifier)
            assert document.embedding_generation == previous_generation
            assert document.status == (
                DocumentStatus.INDEXED if previous_index else DocumentStatus.CHUNKED
            )
            assert len(observer.scalars(select(ChunkEmbedding)).all()) == int(
                previous_index
            )
        assert service.index(identifier, force=True).status == DocumentStatus.INDEXED


def test_provider_failure_preserves_previous_index(tmp_path):
    identifier = chunked_document(LocalDocumentStorage(tmp_path))

    def quota():
        raise EmbeddingQuotaExceeded

    with SessionFactory() as session:
        document = DocumentIndexingService(session, StubEmbeddings()).index(identifier)
        generation = document.embedding_generation
        with pytest.raises(EmbeddingQuotaExceeded):
            DocumentIndexingService(session, StubEmbeddings(quota)).index(
                identifier, force=True
            )
    with SessionFactory() as observer:
        assert observer.get(Document, identifier).embedding_generation == generation
        assert len(observer.scalars(select(ChunkEmbedding)).all()) == 1


@pytest.mark.parametrize("delete_completely", [False, True])
def test_deletion_during_provider_call_prevents_publication(
    tmp_path, delete_completely
):
    storage = LocalDocumentStorage(tmp_path)
    identifier = chunked_document(storage)

    def delete():
        with SessionFactory() as other:
            if delete_completely:
                DocumentService(other, storage).delete(identifier)
            else:
                with other.begin():
                    other.get(Document, identifier).status = DocumentStatus.DELETING

    with SessionFactory() as session:
        with pytest.raises(
            DocumentNotFound if delete_completely else DocumentIndexingConflict
        ):
            DocumentIndexingService(session, StubEmbeddings(delete)).index(identifier)
    with SessionFactory() as observer:
        assert observer.scalars(select(ChunkEmbedding)).all() == []


def test_concurrent_reindex_cannot_overwrite_newer_generation(tmp_path):
    identifier = chunked_document(LocalDocumentStorage(tmp_path))
    generations = []

    def publish():
        with SessionFactory() as other:
            document = DocumentIndexingService(other, StubEmbeddings()).index(
                identifier, force=True
            )
            generations.append(document.embedding_generation)

    with SessionFactory() as session:
        DocumentIndexingService(session, StubEmbeddings()).index(identifier)
        with pytest.raises(DocumentIndexingConflict):
            DocumentIndexingService(session, StubEmbeddings(publish)).index(
                identifier, force=True
            )
    with SessionFactory() as observer:
        assert observer.get(Document, identifier).embedding_generation == generations[0]


@pytest.mark.parametrize("late_failure", [False, True])
def test_late_extraction_preserves_concurrent_index(tmp_path, late_failure):
    from io import BytesIO

    from test_extraction import make_pdf

    from app.documents.exceptions import DocumentExtractionFailed
    from app.documents.extraction import PdfTextExtractor
    from app.documents.extraction_service import DocumentExtractionService

    storage = LocalDocumentStorage(tmp_path)
    with SessionFactory() as setup:
        identifier = (
            DocumentService(setup, storage)
            .upload(
                title="Concurrent",
                filename="a.pdf",
                source=BytesIO(make_pdf("Some text")),
            )
            .id
        )
    generations = []

    class SlowExtraction(PdfTextExtractor):
        def extract(self, source):
            pages = super().extract(source)
            with SessionFactory() as other:
                DocumentExtractionService(other, storage, PdfTextExtractor()).extract(
                    identifier
                )
                DocumentChunkingService(other, TextChunker()).chunk(identifier)
                doc = DocumentIndexingService(other, StubEmbeddings()).index(identifier)
                generations.append(doc.embedding_generation)
            if late_failure:
                raise DocumentExtractionFailed("invalid_pdf")
            return pages

    with SessionFactory() as session:
        service = DocumentExtractionService(session, storage, SlowExtraction())
        if late_failure:
            with pytest.raises(DocumentExtractionFailed):
                service.extract(identifier)
        else:
            service.extract(identifier)
    with SessionFactory() as observer:
        document = observer.get(Document, identifier)
        assert document.status == DocumentStatus.INDEXED
        assert document.embedding_generation == generations[0]
        assert len(observer.scalars(select(ChunkEmbedding)).all()) == 1
