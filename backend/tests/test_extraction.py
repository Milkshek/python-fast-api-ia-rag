from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from sqlalchemy import text

from app.database.session import SessionFactory
from app.main import app


def make_pdf(*pages, encrypted=False):
    writer = PdfWriter()
    for content in pages:
        page = writer.add_blank_page(width=300, height=300)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
        )
        stream = DecodedStreamObject()
        stream.set_data(
            b"BT /F1 12 Tf 20 250 Td (" + content.encode("ascii") + b") Tj ET"
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("secret")
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def upload(client, data):
    response = client.post(
        "/documents/upload",
        data={"title": "Test"},
        files={"file": ("test.pdf", data, "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_extract_pages_preserves_numbers_and_is_repeatable():
    with TestClient(app) as client:
        identifier = upload(client, make_pdf("First page", "", "Third page"))
        url = f"/documents/{identifier}"
        assert client.get(f"{url}/pages").json() == []
        for _ in range(2):
            result = client.post(f"{url}/extract")
            assert result.status_code == 200
            assert result.json()["status"] == "EXTRACTED"
            assert result.json()["extraction_error"] is None
        pages = client.get(f"{url}/pages").json()
        assert [(p["page_number"], p["text"]) for p in pages] == [
            (1, "First page"),
            (2, ""),
            (3, "Third page"),
        ]
        assert all(p["document_id"] == identifier for p in pages)
        assert client.get(f"{url}/pages?offset=1&limit=1").json() == pages[1:2]
        assert client.delete(url).status_code == 204
        with SessionFactory() as observer:
            assert observer.scalar(text("SELECT count(*) FROM document_pages")) == 0


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"%PDF-1.4\ninvalid", "invalid_pdf"),
        (make_pdf(""), "no_extractable_text"),
        (make_pdf("Secret", encrypted=True), "encrypted_pdf"),
    ],
)
def test_extraction_errors_are_persisted_without_pages(content, code):
    with TestClient(app) as client:
        identifier = upload(client, content)
        url = f"/documents/{identifier}"
        for _ in range(2):
            response = client.post(f"{url}/extract")
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == code
            document = client.get(url).json()
            assert document["status"] == "FAILED"
            assert document["extraction_error"] == code
            assert client.get(f"{url}/pages").json() == []


def test_extraction_requires_uploaded_document():
    with TestClient(app) as client:
        missing = f"/documents/{uuid4()}"
        assert client.post(f"{missing}/extract").status_code == 404
        assert client.get(f"{missing}/pages").status_code == 404
        doc = client.post(
            "/documents", json={"title": "Metadata", "filename": "a.pdf"}
        ).json()
        assert client.post(f"/documents/{doc['id']}/extract").status_code == 409


def test_aes_encrypted_pdf_is_rejected_as_encrypted():
    content = (Path(__file__).parent / "fixtures" / "encrypted-aes256.pdf").read_bytes()
    with TestClient(app) as client:
        identifier = upload(client, content)
        result = client.post(f"/documents/{identifier}/extract")
        assert result.status_code == 422
        assert result.json()["detail"]["code"] == "encrypted_pdf"
        document = client.get(f"/documents/{identifier}").json()
        assert document["status"] == "FAILED"
        assert document["extraction_error"] == "encrypted_pdf"
