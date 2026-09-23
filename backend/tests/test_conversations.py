from uuid import uuid4

import pytest
import test_answers
from test_search import indexed_document, vector

from app.database.session import SessionFactory
from app.documents.models import Document, DocumentChunk
from app.documents.status import DocumentStatus

answer_client = test_answers.answer_client


def create_conversation(client, document_id):
    response = client.post("/conversations", json={"document_id": str(document_id)})
    assert response.status_code == 201
    return response.json()


def test_persisted_exchange_reload_and_source_snapshot(answer_client):
    client, _, calls = answer_client
    document_id = indexed_document([vector(1.0, 0.0)])
    conversation = create_conversation(client, document_id)
    path = f"/conversations/{conversation['id']}"
    assert client.get(path).json() == conversation
    response = client.post(path + "/messages", json={"question": "  Préavis ?  "})
    assert response.status_code == 201
    message = response.json()
    assert message["question"] == "Préavis ?"
    assert message["sequence"] == 1
    assert message["answer"] == "Trois mois."
    assert message["conversation_id"] == conversation["id"]
    source = message["sources"][0]["chunk"]
    assert source["document_id"] == str(document_id)
    with SessionFactory.begin() as session:
        chunk = session.get(DocumentChunk, source["id"])
        session.delete(chunk)
    assert client.get(path + "/messages").json() == [message]
    assert len(calls) == 1


def test_conversation_and_message_pagination_isolation(answer_client):
    client, _, _ = answer_client
    first_doc = indexed_document([vector(1.0, 0.0)])
    second_doc = indexed_document([vector(1.0, 0.0)])
    first = create_conversation(client, first_doc)
    second = create_conversation(client, first_doc)
    other = create_conversation(client, second_doc)
    params = {"document_id": str(first_doc), "limit": 1}
    assert client.get("/conversations", params=params).json() == [second]
    assert client.get("/conversations", params={**params, "offset": 1}).json() == [
        first
    ]
    path = f"/conversations/{first['id']}/messages"
    for question in ["Un", "Deux", "Trois"]:
        assert client.post(path, json={"question": question}).status_code == 201
    page = client.get(path, params={"limit": 1, "offset": 1}).json()
    assert [(item["sequence"], item["question"]) for item in page] == [(2, "Deux")]
    assert client.get(f"/conversations/{other['id']}/messages").json() == []


@pytest.mark.parametrize("status,expected", [(429, 429), (500, 503)])
def test_failed_generation_does_not_record_partial_exchange(
    answer_client, status, expected
):
    client, state, calls = answer_client
    conversation = create_conversation(client, indexed_document([vector(1.0, 0.0)]))
    path = f"/conversations/{conversation['id']}/messages"
    state["status"] = status
    assert client.post(path, json={"question": "Q"}).status_code == expected
    assert client.get(path).json() == []
    assert len(calls) == 1
    state["status"] = 200
    assert client.post(path, json={"question": "Q"}).json()["sequence"] == 1


@pytest.mark.parametrize("change", ["delete", "status", "model", "dimensions"])
def test_document_changed_during_generation_not_persisted(answer_client, change):
    client, state, _ = answer_client
    identifier = indexed_document([vector(1.0, 0.0)])
    conversation = create_conversation(client, identifier)

    def mutate():
        with SessionFactory.begin() as session:
            document = session.get(Document, identifier)
            if change == "delete":
                session.delete(document)
            elif change == "status":
                document.status = DocumentStatus.CHUNKED
            elif change == "model":
                document.embedding_model = "old"
            else:
                document.embedding_dimensions = 42

    state["action"] = mutate
    path = f"/conversations/{conversation['id']}"
    assert client.post(path + "/messages", json={"question": "Q"}).status_code == (
        404 if change == "delete" else 409
    )
    if change == "delete":
        assert client.get(path).status_code == 404
    else:
        assert client.get(path + "/messages").json() == []


def test_missing_unindexed_and_validation(answer_client):
    client, _, calls = answer_client
    missing = str(uuid4())
    assert (
        client.post("/conversations", json={"document_id": missing}).status_code == 404
    )
    assert client.get(f"/conversations/{missing}").status_code == 404
    assert client.get(f"/conversations/{missing}/messages").status_code == 404
    assert (
        client.post(
            f"/conversations/{missing}/messages", json={"question": "Q"}
        ).status_code
        == 404
    )
    document = client.post(
        "/documents", json={"title": "D", "filename": "d.pdf"}
    ).json()
    assert (
        client.post("/conversations", json={"document_id": document["id"]}).status_code
        == 409
    )
    for params in [{"limit": 0}, {"limit": 101}, {"offset": -1}]:
        assert (
            client.get(
                "/conversations", params={"document_id": missing, **params}
            ).status_code
            == 422
        )
        assert (
            client.get(f"/conversations/{missing}/messages", params=params).status_code
            == 422
        )
    for payload in [
        {"question": " "},
        {"question": "x" * 2001},
        {"question": "Q", "extra": True},
    ]:
        assert (
            client.post(f"/conversations/{missing}/messages", json=payload).status_code
            == 422
        )
    assert calls == []


def test_document_deletion_cascades_all_history(answer_client):
    from sqlalchemy import func, select

    from app.conversations.models import Conversation, ConversationMessage

    client, _, _ = answer_client
    identifier = indexed_document([vector(1.0, 0.0)])
    conversation = create_conversation(client, identifier)
    path = f"/conversations/{conversation['id']}/messages"
    assert client.post(path, json={"question": "Q"}).status_code == 201
    assert client.delete(f"/documents/{identifier}").status_code == 204
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Conversation)) == 0
        assert (
            session.scalar(select(func.count()).select_from(ConversationMessage)) == 0
        )


def test_publication_failure_rolls_back_exchange(answer_client, monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError

    from app.conversations.repository import ConversationRepository

    client, _, _ = answer_client
    conversation = create_conversation(client, indexed_document([vector(1.0, 0.0)]))
    path = f"/conversations/{conversation['id']}/messages"
    original = ConversationRepository.add_message

    def fail_after_insert(repository, message):
        original(repository, message)
        repository._session.flush()
        raise SQLAlchemyError("simulated database failure")

    with monkeypatch.context() as patch:
        patch.setattr(ConversationRepository, "add_message", fail_after_insert)
        with pytest.raises(SQLAlchemyError):
            client.post(path, json={"question": "Q"})
    assert client.get(path).json() == []
    assert client.post(path, json={"question": "Q"}).json()["sequence"] == 1


def test_concurrent_messages_are_published_with_unique_sequences():
    import json
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    import httpx2 as httpx
    from test_answer_client import response_body

    from app.ai.answers import GeminiAnswerClient
    from app.ai.embeddings import GeminiEmbeddingClient
    from app.conversations.service import ConversationService
    from app.documents.services.answers import DocumentAnswerService
    from app.documents.services.search import DocumentSearchService

    identifier = indexed_document([vector(1.0, 0.0)])
    barrier = Barrier(2)
    seen_questions = []

    def run(question, conversation_id=None):
        with SessionFactory() as session:

            def respond(request):
                assert not session.in_transaction()
                if request.url.path.endswith(":embedContent"):
                    return httpx.Response(
                        200, json={"embedding": {"values": vector(1.0, 0.0)}}
                    )
                seen_questions.append(json.loads(request.content))
                barrier.wait(timeout=5)
                return httpx.Response(200, json=response_body())

            with httpx.Client(transport=httpx.MockTransport(respond)) as http:
                answers = DocumentAnswerService(
                    session,
                    DocumentSearchService(session, GeminiEmbeddingClient("key", http)),
                    GeminiAnswerClient("key", http),
                )
                service = ConversationService(session, answers)
                if conversation_id is None:
                    return service.create(identifier).id
                return service.ask(conversation_id, question=question).sequence

    conversation_id = run("")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(run, question, conversation_id)
            for question in ["Premier", "Second"]
        ]
        assert sorted(future.result(timeout=10) for future in futures) == [1, 2]
    assert len(seen_questions) == 2


def test_questions_are_independent_and_abstention_is_persisted(answer_client):
    import json

    from app.documents.services.answers import ABSTENTION

    client, state, calls = answer_client
    conversation = create_conversation(client, indexed_document([vector(1.0, 0.0)]))
    path = f"/conversations/{conversation['id']}/messages"
    assert client.post(path, json={"question": "PREVIOUS_QUESTION"}).status_code == 201
    state["payload"] = {"answer": "", "abstained": True, "source_ids": []}
    response = client.post(path, json={"question": "CURRENT_QUESTION"})
    assert response.status_code == 201
    message = response.json()
    assert message["answer"] == ABSTENTION
    assert message["abstained"] is True
    assert message["sources"] == []
    assert client.get(path).json()[1] == message
    body = json.loads(calls[1].content)
    assert len(body["contents"]) == 1
    prompt = json.loads(body["contents"][0]["parts"][0]["text"])
    assert set(prompt) == {"question", "passages"}
    assert prompt["question"] == "CURRENT_QUESTION"
    assert "PREVIOUS_QUESTION" not in str(body)
    assert "Trois mois." not in str(body)


@pytest.mark.parametrize("recover", [True, False])
def test_generation_retry_does_not_replay_retrieval_or_publication(
    monkeypatch, recover
):
    import httpx2 as httpx
    from test_answer_client import response_body

    from app.ai import answers as answer_module
    from app.ai.answers import AnswerTemporarilyUnavailable, GeminiAnswerClient
    from app.ai.embeddings import GeminiEmbeddingClient
    from app.conversations.service import ConversationService
    from app.documents.services.answers import DocumentAnswerService
    from app.documents.services.search import DocumentSearchService

    identifier = indexed_document([vector(1.0, 0.0)])
    calls = {"embedding": 0, "generation": 0}
    with SessionFactory() as session:

        def wait(seconds):
            assert not session.in_transaction()

        monkeypatch.setattr(answer_module, "sleep", wait)

        def respond(request):
            assert not session.in_transaction()
            if request.url.path.endswith(":embedContent"):
                calls["embedding"] += 1
                return httpx.Response(
                    200, json={"embedding": {"values": vector(1.0, 0.0)}}
                )
            calls["generation"] += 1
            if recover and calls["generation"] == 3:
                return httpx.Response(200, json=response_body())
            return httpx.Response(503)

        with httpx.Client(transport=httpx.MockTransport(respond)) as http:
            service = ConversationService(
                session,
                DocumentAnswerService(
                    session,
                    DocumentSearchService(session, GeminiEmbeddingClient("key", http)),
                    GeminiAnswerClient("key", http),
                ),
            )
            conversation = service.create(identifier)
            if recover:
                message = service.ask(conversation.id, question="Préavis ?")
                assert message.sequence == 1
            else:
                with pytest.raises(AnswerTemporarilyUnavailable):
                    service.ask(conversation.id, question="Préavis ?")
            assert len(
                service.list_messages(conversation.id, limit=20, offset=0)
            ) == int(recover)
    assert calls == {"embedding": 1, "generation": 3}


@pytest.mark.parametrize("conversation_route", [True, False])
def test_saturation_has_specific_http_message(
    answer_client, monkeypatch, conversation_route
):
    from app.ai import answers

    monkeypatch.setattr(answers, "sleep", lambda seconds: None)
    client, state, calls = answer_client
    identifier = indexed_document([vector(1.0, 0.0)])
    if conversation_route:
        conversation = create_conversation(client, identifier)
        path = f"/conversations/{conversation['id']}/messages"
    else:
        path = f"/documents/{identifier}/ask"
    state["status"] = 503
    response = client.post(path, json={"question": "Q"})
    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Le modèle Gemini est temporairement indisponible. Réessayez dans quelques instants."
    )
    assert len(calls) == 3
    if conversation_route:
        assert client.get(path).json() == []
