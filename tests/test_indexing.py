from fastapi.testclient import TestClient
from test_extraction import make_pdf, upload

from app.main import app


def test_indexing_requires_chunks_and_configuration(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with TestClient(app) as client:
        identifier = upload(client, make_pdf("Texte synthetique pour les embeddings."))
        url = f"/documents/{identifier}"
        assert client.post(f"{url}/index").status_code == 409
        assert client.post(f"{url}/extract").status_code == 200
        assert client.post(f"{url}/chunk").status_code == 200
        response = client.post(f"{url}/index")
        assert response.status_code == 503
        assert client.get(url).json()["status"] == "CHUNKED"


def test_indexed_vectors_are_persistent_repeatable_and_cascade():
    import httpx2 as httpx
    from sqlalchemy import select, text

    from app.ai.embeddings import DIMENSIONS, GeminiEmbeddingClient
    from app.database.session import SessionFactory
    from app.documents.dependencies import get_embedding_client
    from app.documents.models import ChunkEmbedding

    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200, json={"embedding": {"values": [1.0] + [0.0] * (DIMENSIONS - 1)}}
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_embedding_client] = lambda: GeminiEmbeddingClient(
            "key", http
        )
        try:
            with TestClient(app) as client:
                identifier = upload(client, make_pdf("First page", "Second page"))
                url = f"/documents/{identifier}"
                client.post(f"{url}/extract")
                client.post(f"{url}/chunk")
                for _ in range(2):
                    response = client.post(f"{url}/index")
                    assert response.status_code == 200
                    assert response.json()["status"] == "INDEXED"
                    assert response.json()["embedding_model"] == "gemini-embedding-2"
                    assert response.json()["embedding_dimensions"] == 768
                assert len(calls) == 2
                assert client.post(f"{url}/extract").json()["status"] == "INDEXED"
                assert client.post(f"{url}/chunk").json()["status"] == "INDEXED"
                with SessionFactory() as observer:
                    embeddings = observer.scalars(select(ChunkEmbedding)).all()
                    assert len(embeddings) == 2
                    assert len(embeddings[0].vector) == 768
                    assert (
                        observer.scalar(
                            text(
                                "SELECT vector_dims(vector) FROM chunk_embeddings LIMIT 1"
                            )
                        )
                        == 768
                    )
                assert client.post(f"{url}/index?force=true").status_code == 200
                assert len(calls) == 4
                assert client.delete(url).status_code == 204
                with SessionFactory() as observer:
                    assert observer.scalars(select(ChunkEmbedding)).all() == []
        finally:
            app.dependency_overrides.pop(get_embedding_client, None)
