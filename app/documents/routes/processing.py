from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from app.ai.embeddings import (
    EmbeddingLimitExceeded,
    EmbeddingQuotaExceeded,
    EmbeddingUnavailable,
    InvalidEmbeddingResponse,
)
from app.documents.chunking_service import DocumentChunkingService
from app.documents.dependencies import (
    get_document_chunking_service,
    get_document_extraction_service,
    get_document_indexing_service,
)
from app.documents.exceptions import (
    DocumentChunkingConflict,
    DocumentExtractionConflict,
    DocumentExtractionFailed,
    DocumentIndexingConflict,
    DocumentNotFound,
    DocumentStorageUnavailable,
)
from app.documents.extraction_service import DocumentExtractionService
from app.documents.indexing_service import DocumentIndexingService
from app.documents.models import Document, DocumentChunk, DocumentPage
from app.documents.schemas import (
    DocumentChunkRead,
    DocumentPageRead,
    DocumentRead,
)

router = APIRouter()
ExtractionDependency = Annotated[
    DocumentExtractionService, Depends(get_document_extraction_service)
]


@router.post("/{document_id}/extract", response_model=DocumentRead)
def extract_document(document_id: UUID, service: ExtractionDependency) -> Document:
    try:
        return service.extract(document_id)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentExtractionConflict as error:
        raise HTTPException(
            status_code=409, detail="Ce document ne peut pas être extrait"
        ) from error
    except DocumentExtractionFailed as error:
        raise HTTPException(status_code=422, detail={"code": error.code}) from error
    except DocumentStorageUnavailable as error:
        raise HTTPException(status_code=503, detail="Stockage indisponible") from error


@router.get("/{document_id}/pages", response_model=list[DocumentPageRead])
def list_document_pages(
    document_id: UUID,
    service: ExtractionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[DocumentPage]:
    try:
        return service.list_pages(document_id, limit=limit, offset=offset)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error


ChunkingDependency = Annotated[
    DocumentChunkingService, Depends(get_document_chunking_service)
]


@router.post("/{document_id}/chunk", response_model=DocumentRead)
def chunk_document(document_id: UUID, service: ChunkingDependency) -> Document:
    try:
        return service.chunk(document_id)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentChunkingConflict as error:
        raise HTTPException(
            status_code=409, detail="Du texte extrait est requis pour le découpage"
        ) from error


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkRead])
def list_document_chunks(
    document_id: UUID,
    service: ChunkingDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[DocumentChunk]:
    try:
        return service.list_chunks(document_id, limit=limit, offset=offset)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error


IndexingDependency = Annotated[
    DocumentIndexingService, Depends(get_document_indexing_service)
]


@router.post("/{document_id}/index", response_model=DocumentRead)
def index_document(
    document_id: UUID,
    service: IndexingDependency,
    force: bool = False,
) -> Document:
    try:
        return service.index(document_id, force=force)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentIndexingConflict as error:
        raise HTTPException(
            status_code=409, detail="État incompatible ou indexation concurrente"
        ) from error
    except EmbeddingQuotaExceeded as error:
        raise HTTPException(
            status_code=429, detail="Quota Gemini atteint ; réessayer plus tard"
        ) from error
    except EmbeddingUnavailable as error:
        raise HTTPException(
            status_code=503, detail="Gemini indisponible ou configuration manquante"
        ) from error
    except InvalidEmbeddingResponse as error:
        raise HTTPException(
            status_code=502, detail="Réponse d'embedding invalide"
        ) from error
    except EmbeddingLimitExceeded as error:
        raise HTTPException(
            status_code=413, detail="Maximum 100 chunks par indexation locale"
        ) from error
