from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.ai.answers import ContextPassage, GeminiAnswerClient, InvalidAnswerResponse
from app.ai.embeddings import DIMENSIONS, MODEL
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.models import DocumentChunk
from app.documents.repository import DocumentRepository
from app.documents.services.search import DocumentSearchHit, DocumentSearchService
from app.documents.status import DocumentStatus

MAX_PASSAGES = 5
MAX_CONTEXT_CHARACTERS = 5000
ABSTENTION = "Les passages disponibles ne permettent pas de répondre à cette question."


@dataclass(frozen=True)
class AnswerSource:
    id: int
    chunk: DocumentChunk


@dataclass(frozen=True)
class DocumentAnswer:
    answer: str
    abstained: bool
    sources: list[AnswerSource]


class DocumentAnswerService:
    def __init__(
        self,
        session: Session,
        search: DocumentSearchService,
        answers: GeminiAnswerClient,
    ) -> None:
        self._session = session
        self._repository = DocumentRepository(session)
        self._search = search
        self._answers = answers

    def ask(self, document_id: UUID, *, question: str) -> DocumentAnswer:
        hits = self._search.search(document_id, question=question, top_k=MAX_PASSAGES)
        sources = self._select_context(hits)
        if not sources:
            return DocumentAnswer(ABSTENTION, True, [])
        passages = [
            ContextPassage(id=source.id, text=source.chunk.text) for source in sources
        ]
        generated = self._answers.generate(question, passages)
        by_id = {source.id: source for source in sources}
        if (
            len(set(generated.source_ids)) != len(generated.source_ids)
            or any(identifier not in by_id for identifier in generated.source_ids)
            or (generated.abstained and bool(generated.source_ids))
            or (not generated.abstained and not generated.source_ids)
        ):
            raise InvalidAnswerResponse
        self._ensure_document_available(document_id)
        if generated.abstained:
            return DocumentAnswer(ABSTENTION, True, [])
        return DocumentAnswer(
            generated.answer,
            False,
            [by_id[identifier] for identifier in generated.source_ids],
        )

    def _select_context(self, hits: list[DocumentSearchHit]) -> list[AnswerSource]:
        sources: list[AnswerSource] = []
        characters = 0
        for hit in hits[:MAX_PASSAGES]:
            if characters + len(hit.chunk.text) > MAX_CONTEXT_CHARACTERS:
                break
            characters += len(hit.chunk.text)
            sources.append(AnswerSource(id=len(sources) + 1, chunk=hit.chunk))
        return sources

    def _ensure_document_available(self, document_id: UUID) -> None:
        with self._session.begin():
            document = self._repository.get_for_update(document_id)
            if document is None:
                raise DocumentNotFound(document_id)
            if (
                document.status != DocumentStatus.INDEXED
                or document.embedding_model != MODEL
                or document.embedding_dimensions != DIMENSIONS
            ):
                raise DocumentSearchConflict
