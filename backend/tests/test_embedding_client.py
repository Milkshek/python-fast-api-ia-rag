import json

import httpx2 as httpx
import pytest

from app.ai.embeddings import (
    DIMENSIONS,
    MODEL,
    EmbeddingLimitExceeded,
    EmbeddingQuotaExceeded,
    EmbeddingUnavailable,
    GeminiEmbeddingClient,
    InvalidEmbeddingResponse,
)


def test_client_sends_one_document_per_request_without_key_in_url():
    received = []

    def respond(request):
        received.append(request)
        return httpx.Response(
            200, json={"embedding": {"values": [3.0, 4.0] + [0.0] * (DIMENSIONS - 2)}}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = GeminiEmbeddingClient("test-secret", http).embed_documents(
            ["First", "Second"]
        )
    assert result[0][:2] == [0.6, 0.8]
    assert len(received) == 2
    for request, content in zip(received, ["First", "Second"], strict=True):
        assert request.url.host == "generativelanguage.googleapis.com"
        assert MODEL in request.url.path
        assert "test-secret" not in str(request.url)
        assert request.headers["x-goog-api-key"] == "test-secret"
        payload = json.loads(request.content)
        assert payload["content"]["parts"] == [
            {"text": f"title: none | text: {content}"}
        ]
        assert payload["embedContentConfig"] == {
            "outputDimensionality": 768,
            "autoTruncate": False,
        }


@pytest.mark.parametrize(
    ("code", "error"),
    [
        (429, EmbeddingQuotaExceeded),
        (403, EmbeddingUnavailable),
        (500, EmbeddingUnavailable),
    ],
)
def test_provider_errors_are_not_retried(code, error):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(code, json={"error": "not exposed"})

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(error):
            GeminiEmbeddingClient("key", http).embed_documents(["A", "B"])
    assert len(calls) == 1


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"{}",
        b'{"embedding":{"values":[1,2]}}',
        json.dumps({"embedding": {"values": [0.0] * DIMENSIONS}}).encode(),
        json.dumps({"embedding": {"values": [True] * DIMENSIONS}}).encode(),
        json.dumps({"embedding": {"values": [float("inf")] * DIMENSIONS}}).encode(),
    ],
)
def test_invalid_vectors_are_rejected(body):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    ) as http:
        with pytest.raises(InvalidEmbeddingResponse):
            GeminiEmbeddingClient("key", http).embed_documents(["A"])


def test_timeout_is_translated_and_no_secrets_exposed():
    def timeout(request):
        raise httpx.ReadTimeout("timeout with sensitive data", request=request)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as http:
        with pytest.raises(EmbeddingUnavailable) as failure:
            GeminiEmbeddingClient("key", http).embed_documents(["A"])
    assert "sensitive" not in str(failure.value)


def test_missing_key_and_large_documents_do_not_call_provider():
    def unexpected(request):
        pytest.fail("network must not be called")

    with httpx.Client(transport=httpx.MockTransport(unexpected)) as http:
        with pytest.raises(EmbeddingUnavailable):
            GeminiEmbeddingClient("", http).embed_documents(["A"])
        with pytest.raises(EmbeddingLimitExceeded):
            GeminiEmbeddingClient("key", http).embed_documents(["A"] * 101)


def test_query_uses_question_answering_prefix_and_same_dimensions():
    received = []

    def respond(request):
        received.append(request)
        return httpx.Response(
            200, json={"embedding": {"values": [3.0, 4.0] + [0.0] * (DIMENSIONS - 2)}}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        vector = GeminiEmbeddingClient("key", http).embed_query("Quel préavis ?")
    assert vector[:2] == [0.6, 0.8]
    assert len(vector) == DIMENSIONS
    assert len(received) == 1
    payload = json.loads(received[0].content)
    assert payload["content"]["parts"] == [
        {"text": "task: question answering | query: Quel préavis ?"}
    ]
    assert payload["embedContentConfig"]["outputDimensionality"] == DIMENSIONS
    assert MODEL in received[0].url.path
