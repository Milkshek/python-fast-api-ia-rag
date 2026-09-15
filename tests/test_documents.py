from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.database.session import SessionFactory, get_session
from app.documents.models import Document
from app.main import app


def test_document_lifecycle():
    with TestClient(app) as client:
        response = client.post(
            "/documents", json={"title": " Contrat ", "filename": " contrat.pdf "}
        )
        assert response.status_code == 201
        document = response.json()
        assert UUID(document["id"])
        assert document["title"] == "Contrat"
        assert document["filename"] == "contrat.pdf"
        assert datetime.fromisoformat(document["created_at"]).tzinfo is not None
        url = f"/documents/{document['id']}"
        assert response.headers["location"] == url
        assert client.get(url).json() == document
        assert document in client.get("/documents").json()
        deleted = client.delete(url)
        assert deleted.status_code == 204
        assert deleted.content == b""
        assert client.get(url).status_code == 404
        assert client.delete(url).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": "   ", "filename": "a.pdf"},
        {"title": "a", "filename": "\t"},
        {"title": "x" * 201, "filename": "a.pdf"},
        {"title": "a", "filename": "x" * 256},
        {"title": 123, "filename": "a.pdf"},
        {"title": "a", "filename": "a.pdf", "id": str(uuid4())},
    ],
)
def test_invalid_payload_is_rejected_without_persisting(payload):
    with TestClient(app) as client:
        assert client.post("/documents", json=payload).status_code == 422
        assert client.get("/documents").json() == []


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "limit=abc"])
def test_invalid_pagination(query):
    with TestClient(app) as client:
        assert client.get(f"/documents?{query}").status_code == 422


@pytest.mark.parametrize("method", ["get", "delete"])
def test_invalid_and_missing_identifiers(method):
    with TestClient(app) as client:
        assert client.request(method, "/documents/not-a-uuid").status_code == 422
        response = client.request(method, f"/documents/{uuid4()}")
        assert response.status_code == 404
        assert response.json() == {"detail": "Document introuvable"}


def test_pagination_has_stable_order():
    with TestClient(app) as client:
        assert client.get("/documents").json() == []
        documents = [
            client.post("/documents", json={"title": str(i), "filename": "a.pdf"}).json()
            for i in range(3)
        ]
        assert client.get("/documents?limit=2").json() == documents[:2]
        assert client.get("/documents?limit=2&offset=2").json() == documents[2:]
        assert client.get("/documents?offset=3").json() == []


def test_creation_commits_to_postgres():
    with TestClient(app) as client:
        response = client.post("/documents", json={"title": "Persisté", "filename": "a.pdf"})
        assert response.status_code == 201
        identifier = UUID(response.json()["id"])
    # Une nouvelle session SQL prouve que l'écriture ne vit pas seulement dans la requête.
    with SessionFactory() as session:
        document = session.get(Document, identifier)
        assert document is not None
        assert document.title == "Persisté"


def test_unfinished_transaction_is_rolled_back_on_dependency_error():
    dependency = get_session()
    session = next(dependency)
    document = Document(title="Non validé", filename="a.pdf")
    session.add(document)
    session.flush()
    identifier = document.id
    with pytest.raises(RuntimeError, match="interruption"):
        dependency.throw(RuntimeError("interruption"))
    with SessionFactory() as another_session:
        assert another_session.get(Document, identifier) is None
