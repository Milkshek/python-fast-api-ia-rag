import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from app.documents.exceptions import DocumentStorageUnavailable, DocumentTooLarge

logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
COPY_BLOCK_BYTES = 64 * 1024


class LocalDocumentStorage:
    """Fichiers locaux adressés uniquement par UUID ; aucun accès SQL."""

    def __init__(self, root: Path, *, max_bytes: int = MAX_UPLOAD_BYTES) -> None:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")
        self._root = root
        self._max_bytes = max_bytes

    def save(self, document_id: UUID, source: BinaryIO) -> int:
        temporary = self._root / f".{document_id}.part"
        size = 0
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            with temporary.open("xb") as destination:
                while block := source.read(COPY_BLOCK_BYTES):
                    size += len(block)
                    if size > self._max_bytes:
                        raise DocumentTooLarge
                    destination.write(block)
            temporary.replace(self._path(document_id))
            return size
        except OSError as error:
            raise DocumentStorageUnavailable from error
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                logger.exception("Unable to clean partial upload %s", document_id)

    @contextmanager
    def open(self, document_id: UUID) -> Iterator[BinaryIO]:
        try:
            with self._path(document_id).open("rb") as source:
                yield source
        except OSError as error:
            raise DocumentStorageUnavailable from error

    def delete(self, document_id: UUID) -> None:
        try:
            self._path(document_id).unlink(missing_ok=True)
        except OSError as error:
            raise DocumentStorageUnavailable from error

    def _path(self, document_id: UUID) -> Path:
        return self._root / f"{document_id}.pdf"
