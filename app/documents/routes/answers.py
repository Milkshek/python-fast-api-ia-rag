from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.ai.answers import AnswerQuotaExceeded, AnswerUnavailable, InvalidAnswerResponse
from app.ai.embeddings import (
    EmbeddingQuotaExceeded,
    EmbeddingUnavailable,
    InvalidEmbeddingResponse,
)
from app.documents.answer_service import DocumentAnswer, DocumentAnswerService
from app.documents.dependencies import get_document_answer_service
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.schemas.answers import DocumentAnswerRead, DocumentQuestion

router = APIRouter()
AnswerDependency = Annotated[
    DocumentAnswerService, Depends(get_document_answer_service)
]


@router.post("/{document_id}/ask", response_model=DocumentAnswerRead)
def ask_document(
    document_id: UUID, payload: DocumentQuestion, service: AnswerDependency
) -> DocumentAnswer:
    try:
        return service.ask(document_id, question=payload.question)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentSearchConflict as error:
        raise HTTPException(
            status_code=409, detail="Un index compatible est requis pour la recherche"
        ) from error
    except (EmbeddingQuotaExceeded, AnswerQuotaExceeded) as error:
        raise HTTPException(
            status_code=429, detail="Quota Gemini atteint ; réessayer plus tard"
        ) from error
    except (EmbeddingUnavailable, AnswerUnavailable) as error:
        raise HTTPException(
            status_code=503, detail="Gemini indisponible ou configuration manquante"
        ) from error
    except (InvalidEmbeddingResponse, InvalidAnswerResponse) as error:
        raise HTTPException(
            status_code=502, detail="Réponse Gemini invalide"
        ) from error
