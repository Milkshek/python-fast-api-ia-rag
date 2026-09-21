import json

import httpx2 as httpx
import pytest
from fastapi.testclient import TestClient
from test_answer_client import response_body
from test_search import indexed_document, vector

from app.ai.answers import GeminiAnswerClient
from app.ai.embeddings import GeminiEmbeddingClient
from app.database.session import SessionFactory
from app.documents.answer_service import ABSTENTION, DocumentAnswerService
from app.documents.dependencies import get_answer_client, get_embedding_client
from app.documents.models import Document
from app.documents.search_service import DocumentSearchService
from app.documents.status import DocumentStatus
from app.main import app


def test_ask_requires_an_index():
    with TestClient(app) as client:
        document = client.post(
            "/documents", json={"title": "Test", "filename": "test.pdf"}
        ).json()
        assert (
            client.post(
                f"/documents/{document['id']}/ask", json={"question": "Quel préavis ?"}
            ).status_code
            == 409
        )


def test_answer_contains_only_cited_local_sources():
    from app.ai.answers import GeminiAnswerClient
    from app.ai.embeddings import GeminiEmbeddingClient
    from app.documents.dependencies import get_answer_client, get_embedding_client

    identifier = indexed_document([vector(1.0, 0.0), vector(0.6, 0.8)])
    received = []

    def respond(request):
        received.append(request)
        if request.url.path.endswith(":embedContent"):
            return httpx.Response(200, json={"embedding": {"values": vector(1.0, 0.0)}})
        payload = {"answer": "Le passage deux.", "abstained": False, "source_ids": [2]}
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": json.dumps(payload)}]},
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_embedding_client] = lambda: GeminiEmbeddingClient(
            "key", http
        )
        app.dependency_overrides[get_answer_client] = lambda: GeminiAnswerClient(
            "key", http
        )
        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/documents/{identifier}/ask", json={"question": "Question"}
                )
            assert response.status_code == 200
            result = response.json()
            assert result["answer"] == "Le passage deux."
            assert result["abstained"] is False
            assert len(result["sources"]) == 1
            assert result["sources"][0]["id"] == 2
            assert result["sources"][0]["chunk"]["document_id"] == str(identifier)
            assert result["sources"][0]["chunk"]["page_number"] == 2
            assert len(received) == 2
        finally:
            app.dependency_overrides.clear()


@pytest.fixture
def answer_client():
    state = {
        "payload": {"answer": "Trois mois.", "abstained": False, "source_ids": [1]},
        "action": lambda: None,
        "status": 200,
    }
    calls = []

    def respond(request):
        if request.url.path.endswith(":embedContent"):
            return httpx.Response(200, json={"embedding": {"values": vector(1.0, 0.0)}})
        calls.append(request)
        state["action"]()
        return httpx.Response(state["status"], json=response_body(state["payload"]))

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_embedding_client] = lambda: GeminiEmbeddingClient(
            "key", http
        )
        app.dependency_overrides[get_answer_client] = lambda: GeminiAnswerClient(
            "key", http
        )
        try:
            with TestClient(app) as client:
                yield client, state, calls
        finally:
            app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": "A", "abstained": False, "source_ids": [2]},
        {"answer": "A", "abstained": False, "source_ids": []},
        {"answer": "A", "abstained": False, "source_ids": [1, 1]},
        {"answer": "A", "abstained": True, "source_ids": [1]},
    ],
)
def test_invalid_citations_rejected(answer_client, payload):
    client, state, _ = answer_client
    state["payload"] = payload
    identifier = indexed_document([vector(1.0, 0.0)])
    response = client.post(f"/documents/{identifier}/ask", json={"question": "Q"})
    assert response.status_code == 502


def test_abstention_has_no_sources_and_controlled_message(answer_client):
    client, state, _ = answer_client
    state["payload"] = {
        "answer": "Je ne sais pas.",
        "abstained": True,
        "source_ids": [],
    }
    identifier = indexed_document([vector(1.0, 0.0)])
    response = client.post(f"/documents/{identifier}/ask", json={"question": "Q"})
    assert response.status_code == 200
    assert response.json() == {"answer": ABSTENTION, "abstained": True, "sources": []}


def test_no_context_skips_generation(answer_client):
    client, _, calls = answer_client
    identifier = indexed_document([])
    response = client.post(f"/documents/{identifier}/ask", json={"question": "Q"})
    assert response.status_code == 200
    assert response.json()["abstained"] is True
    assert calls == []


@pytest.mark.parametrize("delete", [True, False])
def test_document_changed_during_generation_rejected(answer_client, delete):
    client, state, _ = answer_client
    identifier = indexed_document([vector(1.0, 0.0)])

    def change():
        with SessionFactory.begin() as session:
            document = session.get(Document, identifier)
            if delete:
                session.delete(document)
            else:
                document.status = DocumentStatus.DELETING

    state["action"] = change
    response = client.post(f"/documents/{identifier}/ask", json={"question": "Q"})
    assert response.status_code == (404 if delete else 409)


@pytest.mark.parametrize(("status", "expected"), [(429, 429), (500, 503)])
def test_answer_provider_errors_leave_document_unchanged(
    answer_client, status, expected
):
    client, state, calls = answer_client
    state["status"] = status
    identifier = indexed_document([vector(1.0, 0.0)])
    response = client.post(f"/documents/{identifier}/ask", json={"question": "Q"})
    assert response.status_code == expected
    assert len(calls) == 1
    with SessionFactory() as session:
        assert session.get(Document, identifier).status == DocumentStatus.INDEXED


def test_generation_runs_without_sql_transaction():
    identifier = indexed_document([vector(1.0, 0.0)])
    with SessionFactory() as session:

        def respond(request):
            assert not session.in_transaction()
            if request.url.path.endswith(":embedContent"):
                return httpx.Response(
                    200, json={"embedding": {"values": vector(1.0, 0.0)}}
                )
            return httpx.Response(200, json=response_body())

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            search = DocumentSearchService(session, GeminiEmbeddingClient("key", http))
            result = DocumentAnswerService(
                session, search, GeminiAnswerClient("key", http)
            ).ask(identifier, question="Q")
        assert result.abstained is False
        assert not session.in_transaction()


def test_context_is_bounded_without_cutting_passages():
    from app.documents.models import DocumentChunk
    from app.documents.search_service import DocumentSearchHit

    hits = [DocumentSearchHit(DocumentChunk(text="x" * 1500), 1.0) for _ in range(5)]
    # Test the context selection without any network or database access.
    with SessionFactory() as session, httpx.Client() as http:
        service = DocumentAnswerService(
            session,
            DocumentSearchService(session, GeminiEmbeddingClient("key", http)),
            GeminiAnswerClient("key", http),
        )
        sources = service._select_context(hits)
    assert len(sources) == 3
    assert [source.id for source in sources] == [1, 2, 3]
    assert sum(len(source.chunk.text) for source in sources) == 4500


@pytest.mark.parametrize(
    "payload",
    [{"question": " "}, {"question": "x" * 2001}, {"question": "Q", "top_k": 10}],
)
def test_invalid_question_does_not_generate(answer_client, payload):
    client, _, calls = answer_client
    from uuid import uuid4

    response = client.post(f"/documents/{uuid4()}/ask", json=payload)
    assert response.status_code == 422
    assert calls == []
