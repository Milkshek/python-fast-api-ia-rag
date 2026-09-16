import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.documents.chunking import TextChunker
from app.documents.chunking_service import DocumentChunkingService
from app.documents.extraction import PdfTextExtractor
from app.documents.extraction_service import DocumentExtractionService
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
