from enum import StrEnum


class DocumentStatus(StrEnum):
    METADATA_ONLY = "METADATA_ONLY"
    UPLOADED = "UPLOADED"
    EXTRACTED = "EXTRACTED"
    CHUNKED = "CHUNKED"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    DELETING = "DELETING"
