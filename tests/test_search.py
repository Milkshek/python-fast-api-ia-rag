from uuid import uuid4

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient

from app.ai.embeddings import DIMENSIONS, MODEL, GeminiEmbeddingClient
from app.database.session import SessionFactory
from app.documents.dependencies import get_embedding_client
from app.documents.models import ChunkEmbedding, Document, DocumentChunk, DocumentPage
from app.documents.status import DocumentStatus
from app.main import app


def vector(x, y):
    return [x, y] + [0.0] * (DIMENSIONS - 2)


def indexed_document(vectors):
    with SessionFactory.begin() as session:
        document = Document(
            title="Synthetic",
            filename="synthetic.pdf",
            status=DocumentStatus.INDEXED,
            embedding_model=MODEL,
            embedding_dimensions=DIMENSIONS,
            embedding_generation=uuid4(),
        )
        session.add(document)
        session.flush()
        for index, values in enumerate(vectors, start=1):
            text = f"Passage {index}"
            session.add(
                DocumentPage(document_id=document.id, page_number=index, text=text)
            )
            session.flush()
            chunk = DocumentChunk(
                document_id=document.id,
                page_number=index,
                chunk_index=index,
                start_offset=0,
                end_offset=len(text),
                text=text,
            )
            session.add(chunk)
            session.flush()
            session.add(ChunkEmbedding(chunk_id=chunk.id, vector=values))
        return document.id


@pytest.fixture
def search_client():
    calls = []
    response = {
        "status": 200,
        "body": {"embedding": {"values": vector(1.0, 0.0)}},
        "action": lambda: None,
    }

    def respond(request):
        calls.append(request)
        response["action"]()
        return httpx.Response(response["status"], json=response["body"])

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_embedding_client] = lambda: GeminiEmbeddingClient(
            "key", http
        )
        try:
            with TestClient(app) as client:
                yield client, calls, response
        finally:
            app.dependency_overrides.pop(get_embedding_client, None)


def test_search_ranks_and_filters_before_top_k(search_client):
    client, calls, _ = search_client
    identifier = indexed_document(
        [vector(0.0, 1.0), vector(0.6, 0.8), vector(0.6, 0.8)]
    )
    indexed_document([vector(1.0, 0.0)])  # Closer, but belongs to another document.
    response = client.post(
        f"/documents/{identifier}/search",
        json={"question": "  Quel préavis ?  ", "top_k": 2},
    )
    assert response.status_code == 200
    hits = response.json()
    assert [hit["chunk"]["page_number"] for hit in hits] == [2, 3]
    assert all(hit["chunk"]["document_id"] == str(identifier) for hit in hits)
    assert hits[0]["score"] == pytest.approx(0.6)
    assert hits[0]["chunk"]["text"] == "Passage 2"
    assert hits[0]["chunk"]["start_offset"] == 0
    assert hits[0]["chunk"]["end_offset"] == len("Passage 2")
    assert len(calls) == 1
    assert "query: Quel préavis ?" in calls[0].content.decode()
    default_response = client.post(
        f"/documents/{identifier}/search", json={"question": "Question"}
    )
    assert len(default_response.json()) == 3


@pytest.mark.parametrize(
    "payload",
    [
        {"question": " "},
        {"question": "a" * 2001},
        {"question": "a", "top_k": 0},
        {"question": "a", "top_k": 11},
        {"question": "a", "top_k": True},
        {"question": "a", "top_k": 1.5},
        {"question": "a", "unknown": 1},
    ],
)
def test_invalid_search_does_not_call_provider(search_client, payload):
    client, calls, _ = search_client
    assert client.post(f"/documents/{uuid4()}/search", json=payload).status_code == 422
    assert calls == []


@pytest.mark.parametrize(
    "changes",
    [
        {"status": DocumentStatus.CHUNKED},
        {"status": DocumentStatus.DELETING},
        {"embedding_model": "other"},
        {"embedding_dimensions": 42},
    ],
)
def test_incompatible_index_rejected_before_provider(search_client, changes):
    client, calls, _ = search_client
    identifier = indexed_document([vector(1.0, 0.0)])
    with SessionFactory.begin() as session:
        document = session.get(Document, identifier)
        for key, value in changes.items():
            setattr(document, key, value)
    assert (
        client.post(
            f"/documents/{identifier}/search", json={"question": "Question"}
        ).status_code
        == 409
    )
    assert calls == []


def test_missing_document_does_not_call_provider(search_client):
    client, calls, _ = search_client
    assert (
        client.post(
            f"/documents/{uuid4()}/search", json={"question": "Question"}
        ).status_code
        == 404
    )
    assert calls == []


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (429, {}, 429),
        (500, {}, 503),
        (200, {}, 502),
    ],
)
def test_search_provider_errors(search_client, status, body, expected):
    client, calls, response = search_client
    response.update(status=status, body=body)
    identifier = indexed_document([vector(1.0, 0.0)])
    assert (
        client.post(
            f"/documents/{identifier}/search", json={"question": "Question"}
        ).status_code
        == expected
    )
    assert len(calls) == 1
    with SessionFactory() as session:
        assert session.get(Document, identifier).status == DocumentStatus.INDEXED


@pytest.mark.parametrize("change", ["delete", "model", "status"])
def test_document_rechecked_after_provider_call(search_client, change):
    client, _, response = search_client
    identifier = indexed_document([vector(1.0, 0.0)])

    def modify():
        with SessionFactory.begin() as session:
            document = session.get(Document, identifier)
            if change == "delete":
                session.delete(document)
            elif change == "model":
                document.embedding_model = "other"
            else:
                document.status = DocumentStatus.DELETING

    response["action"] = modify
    result = client.post(
        f"/documents/{identifier}/search", json={"question": "Question"}
    )
    assert result.status_code == (404 if change == "delete" else 409)


def test_query_embedding_runs_without_sql_transaction():
    from app.documents.search_service import DocumentSearchService

    identifier = indexed_document([vector(1.0, 0.0)])
    with SessionFactory() as session:

        def respond(request):
            assert not session.in_transaction()
            return httpx.Response(200, json={"embedding": {"values": vector(1.0, 0.0)}})

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            result = DocumentSearchService(
                session, GeminiEmbeddingClient("key", http)
            ).search(identifier, question="Question", top_k=1)
        assert result[0].score == pytest.approx(1.0)
        assert not session.in_transaction()


def test_search_without_key_preserves_index(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    identifier = indexed_document([vector(1.0, 0.0)])
    with TestClient(app) as client:
        assert (
            client.post(
                f"/documents/{identifier}/search", json={"question": "Question"}
            ).status_code
            == 503
        )


def test_empty_index_returns_no_hits(search_client):
    client, _, _ = search_client
    identifier = indexed_document([])
    assert (
        client.post(
            f"/documents/{identifier}/search", json={"question": "Question"}
        ).json()
        == []
    )


def test_default_top_k_limits_to_five_passages(search_client):
    client, _, _ = search_client
    identifier = indexed_document([vector(1.0, 0.0)] * 6)
    response = client.post(
        f"/documents/{identifier}/search", json={"question": "Question"}
    )
    assert response.status_code == 200
    assert [hit["chunk"]["page_number"] for hit in response.json()] == [1, 2, 3, 4, 5]
