from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.ai.answers import (
    AnswerQuotaExceeded,
    AnswerTemporarilyUnavailable,
    AnswerUnavailable,
    InvalidAnswerResponse,
)
from app.ai.embeddings import (
    EmbeddingQuotaExceeded,
    EmbeddingUnavailable,
    InvalidEmbeddingResponse,
)
from app.conversations.dependencies import get_conversation_service
from app.conversations.exceptions import ConversationNotFound
from app.conversations.models import Conversation, ConversationMessage
from app.conversations.schemas import (
    ConversationCreate,
    ConversationMessageRead,
    ConversationRead,
)
from app.conversations.service import ConversationService
from app.documents.exceptions import DocumentNotFound, DocumentSearchConflict
from app.documents.schemas.answers import DocumentQuestion

router = APIRouter(prefix="/conversations", tags=["Conversations"])
ServiceDependency = Annotated[ConversationService, Depends(get_conversation_service)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


@contextmanager
def map_errors() -> Iterator[None]:
    """Traduction des erreurs métier uniquement à la frontière HTTP."""
    try:
        yield
    except ConversationNotFound as error:
        raise HTTPException(404, "Conversation introuvable") from error
    except DocumentNotFound as error:
        raise HTTPException(404, "Document introuvable") from error
    except DocumentSearchConflict as error:
        raise HTTPException(
            409, "Un index compatible est requis pour la recherche"
        ) from error
    except (EmbeddingQuotaExceeded, AnswerQuotaExceeded) as error:
        raise HTTPException(
            429, "Quota Gemini atteint ; réessayer plus tard"
        ) from error
    except AnswerTemporarilyUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail="Le modèle Gemini est temporairement indisponible. Réessayez dans quelques instants.",
        ) from error
    except (EmbeddingUnavailable, AnswerUnavailable) as error:
        raise HTTPException(
            503, "Gemini indisponible ou configuration manquante"
        ) from error
    except (InvalidEmbeddingResponse, InvalidAnswerResponse) as error:
        raise HTTPException(502, "Réponse Gemini invalide") from error


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(
    payload: ConversationCreate, service: ServiceDependency
) -> Conversation:
    with map_errors():
        return service.create(payload.document_id)


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    document_id: UUID, service: ServiceDependency, limit: Limit = 20, offset: Offset = 0
) -> Sequence[Conversation]:
    return service.list(document_id, limit=limit, offset=offset)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: UUID, service: ServiceDependency) -> Conversation:
    with map_errors():
        return service.get(conversation_id)


@router.get("/{conversation_id}/messages", response_model=list[ConversationMessageRead])
def list_messages(
    conversation_id: UUID,
    service: ServiceDependency,
    limit: Limit = 20,
    offset: Offset = 0,
) -> Sequence[ConversationMessage]:
    with map_errors():
        return service.list_messages(conversation_id, limit=limit, offset=offset)


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessageRead,
    status_code=201,
)
def ask_conversation(
    conversation_id: UUID, payload: DocumentQuestion, service: ServiceDependency
) -> ConversationMessage:
    with map_errors():
        return service.ask(conversation_id, question=payload.question)
