from uuid import UUID


class DocumentNotFound(Exception):
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"Document {document_id} not found")


class EmptyDocumentFile(Exception):
    pass


class UnsupportedDocumentFile(Exception):
    pass


class DocumentTooLarge(Exception):
    pass


class DocumentStorageUnavailable(Exception):
    pass
