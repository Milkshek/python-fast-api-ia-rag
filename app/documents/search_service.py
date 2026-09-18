from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.embeddings import DIMENSIONS, MODEL, GeminiEmbeddingClient
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.models import DocumentChunk
from app.documents.repository import DocumentRepository
from app.documents.status import DocumentStatus


@dataclass(frozen=True)
class DocumentSearchHit:
    chunk: DocumentChunk
    score: float


class DocumentSearchService:
    """Encode la question hors transaction puis recherche dans un index compatible."""

    def __init__(self, session: Session, embeddings: GeminiEmbeddingClient) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._embeddings = embeddings

    def search(
        self, document_id: UUID, *, question: str, top_k: int
    ) -> list[DocumentSearchHit]:
        with self._session.begin():
            self._ensure_searchable(document_id)
        vector = self._embeddings.embed_query(question)
        with self._session.begin():
            # Le verrou protège uniquement la lecture SQL, jamais l'appel Gemini.
            self._ensure_searchable(document_id, lock=True)
            matches = self._repository.search_chunks(document_id, vector, top_k=top_k)
            return [
                DocumentSearchHit(chunk=chunk, score=1.0 - distance)
                for chunk, distance in matches
            ]

    def _ensure_searchable(self, document_id: UUID, *, lock: bool = False) -> None:
        document = (
            self._repository.get_for_update(document_id)
            if lock
            else self._repository.get(document_id)
        )
        if document is None:
            raise DocumentNotFound(document_id)
        if (
            document.status != DocumentStatus.INDEXED
            or document.embedding_model != MODEL
            or document.embedding_dimensions != DIMENSIONS
        ):
            raise DocumentSearchConflict
