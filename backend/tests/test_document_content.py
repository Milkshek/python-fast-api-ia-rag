from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from test_extraction import make_pdf, upload

from app.database.session import SessionFactory
from app.documents.models import Document
from app.documents.status import DocumentStatus
from app.main import app


def test_original_pdf_and_range_responses():
    content = make_pdf("First", "Second")
    with TestClient(app) as client:
        identifier = upload(client, content)
        url = f"/documents/{identifier}/file"
        response = client.get(url)
        assert response.status_code == 200
        assert response.content == content
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"].startswith("inline;")
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        partial = client.get(url, headers={"Range": "bytes=0-4"})
        assert partial.status_code == 206
        assert partial.content == b"%PDF-"
        assert partial.headers["content-range"] == f"bytes 0-4/{len(content)}"
        assert client.get(url, headers={"Range": "bytes=999999-"}).status_code == 416


@pytest.mark.parametrize("replacement", ["missing", "directory", "symlink"])
def test_unavailable_file_returns_503_without_exposing_path(tmp_path, replacement):
    with TestClient(app) as client:
        identifier = upload(client, make_pdf("First"))
        path = tmp_path / "documents" / f"{identifier}.pdf"
        path.unlink()
        if replacement == "directory":
            path.mkdir()
        elif replacement == "symlink":
            other = tmp_path / "private.pdf"
            other.write_bytes(b"private")
            path.symlink_to(other)
        response = client.get(f"/documents/{identifier}/file")
        assert response.status_code == 503
        assert response.json() == {"detail": "Stockage indisponible"}


def test_file_os_error_returns_503(monkeypatch):
    with TestClient(app) as client:
        identifier = upload(client, make_pdf("First"))
        original = Path.lstat

        def denied(path, *args, **kwargs):
            if path.name == f"{identifier}.pdf":
                raise PermissionError("private storage path")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "lstat", denied)
        response = client.get(f"/documents/{identifier}/file")
        assert response.status_code == 503
        assert response.json() == {"detail": "Stockage indisponible"}


def test_file_uses_uuid_instead_of_filename(tmp_path):
    content = make_pdf("Original")
    with TestClient(app) as client:
        identifier = upload(client, content)
        other = tmp_path / "private.pdf"
        other.write_bytes(b"private")
        with SessionFactory.begin() as session:
            document = session.get(Document, UUID(identifier))
            document.filename = str(other)
        response = client.get(f"/documents/{identifier}/file")
        assert response.status_code == 200
        assert response.content == content
        assert str(tmp_path) not in response.headers["content-disposition"]


def test_missing_and_unavailable_documents():
    with TestClient(app) as client:
        missing = uuid4()
        assert client.get(f"/documents/{missing}/file").status_code == 404
        assert client.get(f"/documents/{missing}/pages/1").status_code == 404
        identifier = client.post(
            "/documents", json={"title": "Metadata", "filename": "a.pdf"}
        ).json()["id"]
        assert client.get(f"/documents/{identifier}/file").status_code == 409
        assert client.get(f"/documents/{identifier}/pages/1").status_code == 404
        identifier = upload(client, make_pdf("First"))
        assert client.post(f"/documents/{identifier}/extract").status_code == 200
        with SessionFactory.begin() as session:
            document = session.get(Document, UUID(identifier))
            document.status = DocumentStatus.DELETING
        assert client.get(f"/documents/{identifier}/file").status_code == 409
        assert client.get(f"/documents/{identifier}/pages/1").status_code == 409


def test_page_reads_preserve_numbers_and_blank_text():
    with TestClient(app) as client:
        identifier = upload(client, make_pdf("First", "", "Third"))
        assert client.post(f"/documents/{identifier}/extract").status_code == 200
        for number, text in [(1, "First"), (2, ""), (3, "Third")]:
            response = client.get(f"/documents/{identifier}/pages/{number}")
            assert response.status_code == 200
            assert response.json() == {
                "document_id": identifier,
                "page_number": number,
                "text": text,
            }
        assert client.get(f"/documents/{identifier}/pages/4").status_code == 404
        for invalid in ["0", "-1", "abc"]:
            assert (
                client.get(f"/documents/{identifier}/pages/{invalid}").status_code
                == 422
            )
