from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse

from app.documents.dependencies import get_document_service
from app.documents.exceptions import (
    DocumentContentConflict,
    DocumentNotFound,
    DocumentPageNotFound,
    DocumentStorageUnavailable,
)
from app.documents.models import DocumentPage
from app.documents.schemas.processing import DocumentPageRead
from app.documents.services.documents import DocumentService

router = APIRouter()
ServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
def get_document_file(document_id: UUID, service: ServiceDependency) -> FileResponse:
    try:
        path = service.file_path(document_id)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentContentConflict as error:
        raise HTTPException(
            status_code=409, detail="Le fichier de ce document est indisponible"
        ) from error
    except DocumentStorageUnavailable as error:
        raise HTTPException(status_code=503, detail="Stockage indisponible") from error
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{document_id}.pdf",
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/{document_id}/pages/{page_number}", response_model=DocumentPageRead)
def get_document_page(
    document_id: UUID,
    page_number: Annotated[int, Path(ge=1)],
    service: ServiceDependency,
) -> DocumentPage:
    try:
        return service.get_page(document_id, page_number)
    except DocumentNotFound as error:
        raise HTTPException(status_code=404, detail="Document introuvable") from error
    except DocumentPageNotFound as error:
        raise HTTPException(status_code=404, detail="Page introuvable") from error
    except DocumentContentConflict as error:
        raise HTTPException(
            status_code=409, detail="Ce document est en cours de suppression"
        ) from error
