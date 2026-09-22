from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.documents.dependencies import get_document_storage
from app.documents.storage import LocalDocumentStorage
from app.main import app

# J4 vérifie l'en-tête, pas encore la structure PDF complète (J5).
PDF = b"%PDF-1.4\nexample\n%%EOF\n"


def test_upload_persists_file_and_delete_removes_it(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_STORAGE_PATH", str(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/documents/upload",
            data={"title": " Contrat "},
            files={"file": ("../../contrat.pdf", PDF, "application/pdf")},
        )
        assert response.status_code == 201
        document = response.json()
        identifier = UUID(document["id"])
        assert document["title"] == "Contrat"
        assert document["status"] == "UPLOADED"
        assert document["size_bytes"] == len(PDF)
        path = tmp_path / f"{identifier}.pdf"
        assert path.read_bytes() == PDF
        assert list(tmp_path.iterdir()) == [path]
        assert document in client.get("/documents").json()
        assert client.delete(response.headers["location"]).status_code == 204
        assert not path.exists()
        assert client.get(response.headers["location"]).status_code == 404


@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [("a.pdf", b"", 400), ("a.txt", PDF, 415), ("a.pdf", b"not a pdf", 415)],
)
def test_invalid_upload_leaves_no_document_or_file(
    tmp_path, monkeypatch, filename, content, expected
):
    monkeypatch.setenv("DOCUMENT_STORAGE_PATH", str(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/documents/upload",
            data={"title": "Contrat"},
            files={"file": (filename, content, "application/pdf")},
        )
        assert response.status_code == expected
        assert client.get("/documents").json() == []
    assert list(tmp_path.iterdir()) == []


def test_metadata_only_document_has_no_uploaded_file():
    with TestClient(app) as client:
        response = client.post(
            "/documents", json={"title": "Métadonnées", "filename": "a.pdf"}
        )
        assert response.status_code == 201
        assert response.json()["status"] == "METADATA_ONLY"
        assert response.json()["size_bytes"] is None


@pytest.mark.parametrize(("size", "expected"), [(32, 201), (33, 413)])
def test_upload_size_limit(tmp_path, size, expected):
    app.dependency_overrides[get_document_storage] = lambda: LocalDocumentStorage(
        tmp_path, max_bytes=32
    )
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                data={"title": "Limite"},
                files={
                    "file": ("a.pdf", b"%PDF-" + b"x" * (size - 5), "application/pdf")
                },
            )
            assert response.status_code == expected
            if expected == 413:
                assert client.get("/documents").json() == []
                assert list(tmp_path.iterdir()) == []
    finally:
        app.dependency_overrides.pop(get_document_storage)


@pytest.mark.parametrize(
    ("title", "filename"),
    [("   ", "a.pdf"), ("x" * 201, "a.pdf"), ("A", "x" * 256 + ".pdf")],
)
def test_invalid_upload_metadata(tmp_path, monkeypatch, title, filename):
    monkeypatch.setenv("DOCUMENT_STORAGE_PATH", str(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/documents/upload", data={"title": title}, files={"file": (filename, PDF)}
        )
        assert response.status_code == 422
        assert client.get("/documents").json() == []
    assert list(tmp_path.iterdir()) == []


def test_duplicate_filenames_do_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCUMENT_STORAGE_PATH", str(tmp_path))
    with TestClient(app) as client:
        first = client.post(
            "/documents/upload", data={"title": "Un"}, files={"file": ("a.pdf", PDF)}
        )
        second = client.post(
            "/documents/upload",
            data={"title": "Deux"},
            files={"file": ("a.pdf", PDF + b"second")},
        )
        assert first.status_code == second.status_code == 201
        assert first.json()["id"] != second.json()["id"]
        assert (tmp_path / f"{first.json()['id']}.pdf").read_bytes() == PDF
        assert (tmp_path / f"{second.json()['id']}.pdf").read_bytes() == PDF + b"second"


def test_disk_error_returns_503_without_exposing_path(tmp_path, monkeypatch):
    root = tmp_path / "not-a-directory"
    root.write_text("existing file")
    monkeypatch.setenv("DOCUMENT_STORAGE_PATH", str(root))
    with TestClient(app) as client:
        response = client.post(
            "/documents/upload", data={"title": "A"}, files={"file": ("a.pdf", PDF)}
        )
        assert response.status_code == 503
        assert response.json() == {"detail": "Stockage indisponible"}
        assert client.get("/documents").json() == []
