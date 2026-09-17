from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.ai.embeddings import DIMENSIONS, MODEL, GeminiEmbeddingClient
from app.documents.exceptions import DocumentIndexingConflict, DocumentNotFound
from app.documents.models import ChunkEmbedding, Document
from app.documents.repository import DocumentRepository
from app.documents.status import DocumentStatus


class DocumentIndexingService:
    """Calcul distant hors transaction, remplacement atomique sous verrou."""

    def __init__(self, session: Session, embeddings: GeminiEmbeddingClient) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._embeddings = embeddings

    def index(self, document_id: UUID, *, force: bool = False) -> Document:
        with self._session.begin():
            document = self._require_document(document_id)
            self._ensure_indexable(document)
            if document.status == DocumentStatus.INDEXED and not force:
                if (
                    document.embedding_model != MODEL
                    or document.embedding_dimensions != DIMENSIONS
                ):
                    raise DocumentIndexingConflict
                return document
            generation = document.embedding_generation
            chunks = self._repository.all_chunks(document_id)
            if not chunks:
                raise DocumentIndexingConflict
        vectors = self._embeddings.embed_documents([chunk.text for chunk in chunks])
        embeddings = [
            ChunkEmbedding(chunk_id=chunk.id, vector=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        return self._publish(document_id, generation, embeddings)

    def _publish(
        self,
        document_id: UUID,
        generation: UUID | None,
        embeddings: list[ChunkEmbedding],
    ) -> Document:
        with self._session.begin():
            document = self._require_document(document_id, lock=True)
            self._ensure_indexable(document)
            if document.embedding_generation != generation:
                # Une autre indexation a terminé pendant l'appel distant.
                raise DocumentIndexingConflict
            self._repository.replace_embeddings(document_id, embeddings)
            document.embedding_model = MODEL
            document.embedding_dimensions = DIMENSIONS
            document.embedding_generation = uuid4()
            document.status = DocumentStatus.INDEXED
        return document

    def _require_document(self, document_id: UUID, *, lock: bool = False) -> Document:
        document = (
            self._repository.get_for_update(document_id)
            if lock
            else self._repository.get(document_id)
        )
        if document is None:
            raise DocumentNotFound(document_id)
        return document

    def _ensure_indexable(self, document: Document) -> None:
        if document.status not in (DocumentStatus.CHUNKED, DocumentStatus.INDEXED):
            raise DocumentIndexingConflict
