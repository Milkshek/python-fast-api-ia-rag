import unicodedata
from dataclasses import dataclass
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import DependencyError, PyPdfError

from app.documents.exceptions import DocumentExtractionFailed


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str


class PdfTextExtractor:
    """Extraction de texte existant, sans OCR ni accès SQL."""

    def __init__(
        self, *, max_pages: int = 200, max_characters: int = 2_000_000
    ) -> None:
        if max_pages <= 0 or max_characters <= 0:
            raise ValueError("Extraction limits must be positive")
        self._max_pages = max_pages
        self._max_characters = max_characters

    def extract(self, source: BinaryIO) -> list[ExtractedPage]:
        try:
            reader = PdfReader(source, strict=True)
            if reader.is_encrypted:
                raise DocumentExtractionFailed("encrypted_pdf")
            if len(reader.pages) > self._max_pages:
                raise DocumentExtractionFailed("extraction_limit_exceeded")
            pages = []
            character_count = 0
            for number, page in enumerate(reader.pages, start=1):
                content = self._normalize(page.extract_text())
                character_count += len(content)
                if character_count > self._max_characters:
                    raise DocumentExtractionFailed("extraction_limit_exceeded")
                pages.append(ExtractedPage(number, content))
        except DependencyError as error:
            # PdfReader peut tenter AES avant de rendre is_encrypted accessible.
            raise DocumentExtractionFailed("encrypted_pdf") from error
        except (PyPdfError, ValueError, KeyError, TypeError, IndexError) as error:
            raise DocumentExtractionFailed("invalid_pdf") from error
        if not any(page.text for page in pages):
            raise DocumentExtractionFailed("no_extractable_text")
        return pages

    def _normalize(self, content: str) -> str:
        content = unicodedata.normalize("NFC", content)
        content = content.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        return "\n".join(line.rstrip() for line in content.split("\n")).strip()
