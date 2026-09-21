import os
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

import httpx2 as httpx
from fastapi import Depends
from sqlalchemy.orm import Session

from app.ai.answers import GeminiAnswerClient
from app.ai.embeddings import GeminiEmbeddingClient
from app.database.session import get_session
from app.documents.answer_service import DocumentAnswerService
from app.documents.chunking import TextChunker
from app.documents.chunking_service import DocumentChunkingService
from app.documents.extraction import PdfTextExtractor
from app.documents.extraction_service import DocumentExtractionService
from app.documents.indexing_service import DocumentIndexingService
from app.documents.search_service import DocumentSearchService
from app.documents.service import DocumentService
from app.documents.storage import LocalDocumentStorage


def get_document_storage() -> LocalDocumentStorage:
    return LocalDocumentStorage(
        Path(os.environ.get("DOCUMENT_STORAGE_PATH", "/data/documents"))
    )


def get_document_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[LocalDocumentStorage, Depends(get_document_storage)],
) -> DocumentService:
    return DocumentService(session, storage)


def get_document_extraction_service(
    session: Annotated[Session, Depends(get_session)],
    storage: Annotated[LocalDocumentStorage, Depends(get_document_storage)],
) -> DocumentExtractionService:
    return DocumentExtractionService(session, storage, PdfTextExtractor())


def get_document_chunking_service(
    session: Annotated[Session, Depends(get_session)],
) -> DocumentChunkingService:
    return DocumentChunkingService(session, TextChunker())


def get_embedding_client() -> Iterator[GeminiEmbeddingClient]:
    with httpx.Client(follow_redirects=False, timeout=15) as http:
        yield GeminiEmbeddingClient(os.environ.get("GEMINI_API_KEY", ""), http)


def get_document_indexing_service(
    session: Annotated[Session, Depends(get_session)],
    embeddings: Annotated[GeminiEmbeddingClient, Depends(get_embedding_client)],
) -> DocumentIndexingService:
    return DocumentIndexingService(session, embeddings)


def get_document_search_service(
    session: Annotated[Session, Depends(get_session)],
    embeddings: Annotated[GeminiEmbeddingClient, Depends(get_embedding_client)],
) -> DocumentSearchService:
    return DocumentSearchService(session, embeddings)


def get_answer_client() -> Iterator[GeminiAnswerClient]:
    with httpx.Client(follow_redirects=False, timeout=30) as http:
        yield GeminiAnswerClient(os.environ.get("GEMINI_API_KEY", ""), http)


def get_document_answer_service(
    session: Annotated[Session, Depends(get_session)],
    search: Annotated[DocumentSearchService, Depends(get_document_search_service)],
    answers: Annotated[GeminiAnswerClient, Depends(get_answer_client)],
) -> DocumentAnswerService:
    return DocumentAnswerService(session, search, answers)
