from io import BytesIO

import pytest
from pypdf import PdfReader


def test_corpus_has_three_documents_ten_questions_and_two_abstentions():
    from evaluation.run import load_corpus

    corpus = load_corpus()
    assert len(corpus.documents) == 3
    assert len(corpus.cases) == 10
    assert sum(case.abstain for case in corpus.cases) == 2


def test_pdf_preserves_pages_and_text():
    from evaluation.run import make_pdf

    pages = ["First page", "Text with (parentheses) and \\ backslash."]
    reader = PdfReader(BytesIO(make_pdf(pages)))
    assert [page.extract_text() for page in reader.pages] == pages


def test_report_checks_full_source_not_only_existing_id():
    from evaluation.run import evaluate_response, load_corpus

    case = load_corpus().cases[0]
    chunk = {
        "id": "known",
        "document_id": "document",
        "page_number": 1,
        "text": "Trois mois.",
        "start_offset": 0,
        "end_offset": 11,
        "chunk_index": 1,
    }
    payload = {
        "answer": "Trois mois.",
        "abstained": False,
        "sources": [{"id": 1, "chunk": chunk}],
    }
    assert evaluate_response(case, payload, {"known": chunk}) == []
    payload["sources"][0]["chunk"] = dict(chunk, text="999 mois.")
    assert "invalid_source" in evaluate_response(case, payload, {"known": chunk})


def test_valid_citation_does_not_prove_factual_accuracy():
    from evaluation.run import evaluate_response, load_corpus

    case = load_corpus().cases[0]
    chunk = {"id": "known", "page_number": 1}
    payload = {
        "answer": "999 mois.",
        "abstained": False,
        "sources": [{"id": 1, "chunk": chunk}],
    }
    # Mechanical checks deliberately do not label this factually correct.
    assert evaluate_response(case, payload, {"known": chunk}) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"answer": "A", "abstained": False, "sources": []},
        {
            "answer": "A",
            "abstained": True,
            "sources": [{"id": 1, "chunk": {"id": "unknown", "page_number": 1}}],
        },
    ],
)
def test_report_rejects_missing_or_unknown_sources(payload):
    from evaluation.run import evaluate_response, load_corpus

    assert evaluate_response(load_corpus().cases[0], payload, {})


def test_setup_failure_cleans_only_created_document_and_saves_report(tmp_path):
    import httpx2 as httpx

    from evaluation.run import run_evaluation

    calls = []

    def respond(request):
        calls.append((request.method, request.url.path))
        if request.url.path == "/documents/upload":
            return httpx.Response(201, json={"id": "created-only"})
        if request.method == "DELETE":
            return httpx.Response(204)
        return httpx.Response(429)

    path = tmp_path / "report.json"
    with httpx.Client(
        base_url="http://api", transport=httpx.MockTransport(respond)
    ) as client:
        report = run_evaluation(client, path)
    assert report["status"] == "incomplete"
    assert report["setup_http_status"] == 429
    assert calls == [
        ("POST", "/documents/upload"),
        ("POST", "/documents/created-only/extract"),
        ("DELETE", "/documents/created-only"),
    ]
    assert path.exists()
    assert report["cleanup_errors"] == []


def test_quota_stops_questions_and_records_failed_cleanup(tmp_path):
    import httpx2 as httpx

    from evaluation.run import run_evaluation

    uploaded = []
    asked = []
    deleted = []

    def respond(request):
        path = request.url.path
        if path == "/documents/upload":
            identifier = str(len(uploaded) + 1)
            uploaded.append(identifier)
            return httpx.Response(201, json={"id": identifier})
        if request.method == "DELETE":
            deleted.append(path)
            return httpx.Response(503 if path.endswith("/2") else 204)
        if path.endswith("/chunks"):
            return httpx.Response(200, json=[])
        if path.endswith("/ask"):
            asked.append(path)
            return httpx.Response(429)
        return httpx.Response(200, json={})

    with httpx.Client(
        base_url="http://api", transport=httpx.MockTransport(respond)
    ) as client:
        report = run_evaluation(client, tmp_path / "report.json")
    assert report["status"] == "quota_reached"
    assert len(asked) == 1
    assert len(deleted) == 3
    assert report["cleanup_errors"] == ["2"]
    assert report["results"][0]["issues"] == ["request_failed"]
