from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.documents.dependencies import (
    get_document_service,
)
from app.documents.exceptions import (
    DocumentNotFound,
    DocumentStorageUnavailable,
    DocumentTooLarge,
    EmptyDocumentFile,
    UnsupportedDocumentFile,
)
from app.documents.models import Document
from app.documents.schemas.documents import (
    DocumentCreate,
    DocumentRead,
)
from app.documents.service import DocumentService

router = APIRouter()
ServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentCreate, response: Response, service: ServiceDependency
) -> Document:
    document = service.create(title=payload.title, filename=payload.filename)
    response.headers["Location"] = f"/documents/{document.id}"
    return document


@router.post(
    "/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED
)
def upload_document(
    title: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    response: Response,
    service: ServiceDependency,
) -> Document:
    try:
        payload = DocumentCreate(title=title, filename=file.filename or "")
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from error
    try:
        document = service.upload(
            title=payload.title, filename=payload.filename, source=file.file
        )
    except EmptyDocumentFile as error:
        raise HTTPException(status_code=400, detail="Le fichier est vide") from error
    except UnsupportedDocumentFile as error:
        raise HTTPException(
            status_code=415, detail="Un fichier PDF est requis"
        ) from error
    except DocumentTooLarge as error:
        raise HTTPException(
            status_code=413, detail="Le PDF dépasse la taille autorisée"
        ) from error
    except DocumentStorageUnavailable as error:
        raise HTTPException(status_code=503, detail="Stockage indisponible") from error
    response.headers["Location"] = f"/documents/{document.id}"
    return document


@router.get("", response_model=list[DocumentRead])
def list_documents(
    service: ServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Sequence[Document]:
    return service.list(limit=limit, offset=offset)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: UUID, service: ServiceDependency) -> Document:
    try:
        return service.get(document_id)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, service: ServiceDependency) -> Response:
    try:
        service.delete(document_id)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentStorageUnavailable as error:
        raise HTTPException(
            status_code=503, detail="Stockage indisponible ; réessayer la suppression"
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
