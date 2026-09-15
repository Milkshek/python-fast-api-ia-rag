from enum import StrEnum


class DocumentStatus(StrEnum):
    METADATA_ONLY = "METADATA_ONLY"
    UPLOADED = "UPLOADED"
    DELETING = "DELETING"
