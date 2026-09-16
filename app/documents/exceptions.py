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


class DocumentExtractionConflict(Exception):
    pass


class DocumentExtractionFailed(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
