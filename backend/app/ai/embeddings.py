import math
import time
from collections.abc import Sequence
from typing import Annotated

import httpx2 as httpx
from pydantic import BaseModel, Field, ValidationError

MODEL = "gemini-embedding-2"
DIMENSIONS = 768
MAX_CHUNKS = 100
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:embedContent"
)


class EmbeddingUnavailable(Exception):
    pass


class EmbeddingQuotaExceeded(Exception):
    pass


class InvalidEmbeddingResponse(Exception):
    pass


class EmbeddingLimitExceeded(Exception):
    pass


class _Embedding(BaseModel):
    values: list[Annotated[float, Field(strict=True, allow_inf_nan=False)]] = Field(
        min_length=DIMENSIONS, max_length=DIMENSIONS
    )


class _Response(BaseModel):
    embedding: _Embedding


class GeminiEmbeddingClient:
    """Un appel REST par chunk ; aucun retry ou changement de modèle implicite."""

    def __init__(self, api_key: str, http: httpx.Client) -> None:
        self._api_key = api_key
        self._http = http

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not self._api_key:
            raise EmbeddingUnavailable
        if len(texts) > MAX_CHUNKS:
            raise EmbeddingLimitExceeded
        deadline = time.monotonic() + 120
        vectors = []
        for text in texts:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EmbeddingUnavailable
            vectors.append(
                self._embed(f"title: none | text: {text}", min(15, remaining))
            )
        return vectors

    def embed_query(self, question: str) -> list[float]:
        if not self._api_key:
            raise EmbeddingUnavailable
        return self._embed(f"task: question answering | query: {question}", 15)

    def _embed(self, content: str, timeout: float) -> list[float]:
        try:
            response = self._http.post(
                ENDPOINT,
                headers={"x-goog-api-key": self._api_key},
                json={
                    "content": {"parts": [{"text": content}]},
                    "embedContentConfig": {
                        "outputDimensionality": DIMENSIONS,
                        "autoTruncate": False,
                    },
                },
                timeout=timeout,
            )
        except httpx.RequestError:
            raise EmbeddingUnavailable from None
        if response.status_code == 429:
            raise EmbeddingQuotaExceeded
        if response.status_code != 200:
            # Ne pas exposer le corps fournisseur, qui peut contenir des données.
            raise EmbeddingUnavailable
        try:
            values = _Response.model_validate_json(response.content).embedding.values
        except ValidationError:
            raise InvalidEmbeddingResponse from None
        norm = math.hypot(*values)
        if not math.isfinite(norm) or norm == 0:
            raise InvalidEmbeddingResponse
        # Normalisation explicite avant stockage float32 et comparaison future.
        return [value / norm for value in values]
