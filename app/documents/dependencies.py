import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.session import get_session
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
