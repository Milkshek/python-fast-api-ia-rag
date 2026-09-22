"""Contrôle d'installation sur projet Compose éphémère, sans fournisseur IA."""

import httpx2 as httpx

from evaluation.run import make_pdf


def main() -> None:
    with httpx.Client(base_url="http://api:8000", timeout=30) as client:
        health = client.get("/health")
        health.raise_for_status()
        assert health.json() == {"status": "ok"}
        assert client.get("/documents").json() == [], "Expected an empty smoke database"
        pdf = make_pdf(["The support team responds within 48 hours."])
        uploaded = client.post(
            "/documents/upload",
            data={"title": "Installation smoke test"},
            files={"file": ("smoke.pdf", pdf, "application/pdf")},
        )
        uploaded.raise_for_status()
        identifier = uploaded.json()["id"]
        path = f"/documents/{identifier}"
        for operation, status in (("extract", "EXTRACTED"), ("chunk", "CHUNKED")):
            response = client.post(f"{path}/{operation}")
            response.raise_for_status()
            assert response.json()["status"] == status
        page = client.get(f"{path}/pages/1")
        page.raise_for_status()
        assert "48 hours" in page.json()["text"]
        original = client.get(f"{path}/file")
        original.raise_for_status()
        assert original.content == pdf
        partial = client.get(f"{path}/file", headers={"Range": "bytes=0-4"})
        assert partial.status_code == 206 and partial.content == b"%PDF-"
        # La clé est explicitement vide dans compose.smoke.yaml : pas d'appel IA.
        assert client.post(f"{path}/index").status_code == 503
        conversation = client.post("/conversations", json={"document_id": identifier})
        assert conversation.status_code == 409
        # Reproduire le Host du navigateur local sans élargir allowedHosts de Vite.
        browser_headers = {"Host": "localhost:5173"}
        frontend = client.get("http://frontend:5173/", headers=browser_headers)
        frontend.raise_for_status()
        assert '<div id="root"></div>' in frontend.text
        proxy = client.get(
            f"http://frontend:5173/api{path}/pages/1", headers=browser_headers
        )
        proxy.raise_for_status()
        assert proxy.json() == page.json()
        malformed = client.post(
            "/documents/upload",
            data={"title": "Invalid synthetic PDF"},
            files={"file": ("invalid.pdf", b"%PDF-not-a-valid-pdf", "application/pdf")},
        )
        malformed.raise_for_status()
        malformed_path = f"/documents/{malformed.json()['id']}"
        assert client.post(f"{malformed_path}/extract").status_code == 422
        assert client.get(malformed_path).json()["status"] == "FAILED"
        for document_path in (path, malformed_path):
            assert client.delete(document_path).status_code == 204
        print(
            "Clean install: API, SQL, upload, extraction, chunks, pages, PDF, errors and frontend proxy OK"
        )


if __name__ == "__main__":
    main()
