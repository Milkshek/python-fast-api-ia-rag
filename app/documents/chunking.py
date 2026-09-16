from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    start_offset: int
    end_offset: int
    text: str


class TextChunker:
    """Fenêtres de caractères déterministes dans le texte d'une seule page."""

    def __init__(self, *, chunk_size: int = 1000, overlap: int = 200) -> None:
        if chunk_size <= 0 or not 0 <= overlap < chunk_size:
            raise ValueError("Require chunk_size > 0 and 0 <= overlap < chunk_size")
        self._chunk_size = chunk_size
        self._overlap = overlap

    def split(self, text: str) -> list[TextChunk]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self._chunk_size, len(text))
            content = text[start:end]
            if content.strip():
                chunks.append(TextChunk(start, end, content))
            if end == len(text):
                break
            start = end - self._overlap
        return chunks
