from fastapi.testclient import TestClient
from sqlalchemy import text
from test_extraction import make_pdf, upload

from app.database.session import SessionFactory
from app.main import app


def test_chunking_is_traceable_repeatable_and_preserves_extraction():
    with TestClient(app) as client:
        content = "abcdefghij " * 210
        identifier = upload(client, make_pdf(content, "", "Last page"))
        url = f"/documents/{identifier}"
        assert client.post(f"{url}/chunk").status_code == 409
        assert client.post(f"{url}/extract").status_code == 200
        pages = {p["page_number"]: p["text"] for p in client.get(f"{url}/pages").json()}
        response = client.post(f"{url}/chunk")
        assert response.status_code == 200
        assert response.json()["status"] == "CHUNKED"
        chunks = client.get(f"{url}/chunks").json()
        assert len(chunks) == 4
        assert [c["chunk_index"] for c in chunks] == [1, 2, 3, 4]
        assert [c["page_number"] for c in chunks] == [1, 1, 1, 3]
        for chunk in chunks:
            assert chunk["document_id"] == identifier
            assert (
                chunk["text"]
                == pages[chunk["page_number"]][
                    chunk["start_offset"] : chunk["end_offset"]
                ]
            )
            assert len(chunk["text"]) <= 1000
        assert chunks[0]["text"][-200:] == chunks[1]["text"][:200]
        assert client.get(f"{url}/chunks?limit=1&offset=1").json() == chunks[1:2]
        assert client.post(f"{url}/chunk").json()["status"] == "CHUNKED"
        assert client.post(f"{url}/extract").json()["status"] == "CHUNKED"
        assert client.get(f"{url}/chunks").json() == chunks
        assert client.delete(url).status_code == 204
        with SessionFactory() as observer:
            assert observer.scalar(text("SELECT count(*) FROM document_chunks")) == 0
