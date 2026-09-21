from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.ai.embeddings import (
    EmbeddingQuotaExceeded,
    EmbeddingUnavailable,
    InvalidEmbeddingResponse,
)
from app.documents.dependencies import get_document_search_service
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.schemas.search import DocumentSearchHitRead, DocumentSearchRequest
from app.documents.search_service import DocumentSearchHit, DocumentSearchService

router = APIRouter()
SearchDependency = Annotated[
    DocumentSearchService, Depends(get_document_search_service)
]


@router.post("/{document_id}/search", response_model=list[DocumentSearchHitRead])
def search_document(
    document_id: UUID, payload: DocumentSearchRequest, service: SearchDependency
) -> list[DocumentSearchHit]:
    try:
        return service.search(
            document_id, question=payload.question, top_k=payload.top_k
        )
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentSearchConflict as error:
        raise HTTPException(
            status_code=409, detail="Un index compatible est requis pour la recherche"
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
