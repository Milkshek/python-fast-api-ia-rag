"""Évaluation explicite via l'API locale ; les tests ordinaires n'appellent pas Gemini."""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from typing import Any
from uuid import uuid4

import httpx2 as httpx
from pydantic import BaseModel, ConfigDict, ValidationError
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.ai.answers import MODEL as ANSWER_MODEL
from app.ai.embeddings import DIMENSIONS
from app.ai.embeddings import MODEL as EMBEDDING_MODEL
from app.documents.schemas.answers import DocumentAnswerRead

CORPUS_PATH = Path(__file__).with_name("corpus.json")


class CorpusDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    pages: list[str]


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    document_id: str
    question: str
    expected_answer: str
    expected_pages: list[int]
    abstain: bool


class Corpus(BaseModel):
    documents: list[CorpusDocument]
    cases: list[EvaluationCase]


def load_corpus() -> Corpus:
    return Corpus.model_validate_json(CORPUS_PATH.read_text())


def make_pdf(pages: list[str]) -> bytes:
    """Crée des pages synthétiques ASCII avec une correspondance texte/page stable."""
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=595, height=842)
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
        lines = wrap(text, width=90) or [""]
        commands = []
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.append(f"({escaped}) Tj")
        stream = DecodedStreamObject()
        stream.set_data(
            ("BT /F1 10 Tf 12 TL 20 800 Td " + " T* ".join(commands) + " ET").encode(
                "ascii"
            )
        )
        page[NameObject("/Contents")] = writer._add_object(stream)
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


def evaluate_response(
    case: EvaluationCase, payload: dict[str, Any], chunks: dict[str, dict[str, Any]]
) -> list[str]:
    """Contrôles mécaniques seulement : aucun jugement de vérité par mots-clés."""
    issues = []
    if payload["abstained"] != case.abstain:
        issues.append("unexpected_abstention")
    sources = payload["sources"]
    if bool(sources) == payload["abstained"]:
        issues.append("inconsistent_sources")
    if any(chunks.get(source["chunk"]["id"]) != source["chunk"] for source in sources):
        issues.append("invalid_source")
    cited_pages = {source["chunk"]["page_number"] for source in sources}
    if not set(case.expected_pages).issubset(cited_pages):
        issues.append("missing_expected_page")
    return issues


def _prepare_document(
    client: httpx.Client, document_id: str
) -> dict[str, dict[str, Any]]:
    for operation in ("extract", "chunk", "index"):
        response = client.post(f"/documents/{document_id}/{operation}")
        response.raise_for_status()
    response = client.get(f"/documents/{document_id}/chunks", params={"limit": 100})
    response.raise_for_status()
    return {chunk["id"]: chunk for chunk in response.json()}


def _run_case(
    client: httpx.Client,
    case: EvaluationCase,
    document_id: str,
    chunks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    started = time.monotonic()
    result: dict[str, Any] = {"case": case.model_dump(), "human_review": None}
    try:
        response = client.post(
            f"/documents/{document_id}/ask", json={"question": case.question}
        )
        result["http_status"] = response.status_code
        response.raise_for_status()
        payload = response.json()
        DocumentAnswerRead.model_validate(payload)
        result["response"] = payload
        result["issues"] = evaluate_response(case, payload, chunks)
    except (httpx.HTTPError, ValidationError, ValueError) as error:
        # Ne pas consigner de corps d'erreur potentiellement sensible.
        result["error"] = type(error).__name__
        result["issues"] = ["request_failed"]
    result["seconds"] = round(time.monotonic() - started, 3)
    return result


def run_evaluation(client: httpx.Client, report_path: Path) -> dict[str, Any]:
    corpus = load_corpus()
    report: dict[str, Any] = {
        "started_at": datetime.now(UTC).isoformat(),
        "corpus_sha256": hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(),
        "configured_models": {
            "answer": ANSWER_MODEL,
            "embedding": EMBEDDING_MODEL,
            "dimensions": DIMENSIONS,
        },
        "status": "incomplete",
        "documents": {},
        "results": [],
        "cleanup_errors": [],
        "review_note": "Contrôles mécaniques uniquement ; justesse et soutien factuel à relire.",
    }
    created: list[str] = []
    chunks_by_document: dict[str, dict[str, dict[str, Any]]] = {}
    report_path.parent.mkdir(parents=True, exist_ok=True)

    def save() -> None:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    try:
        for document in corpus.documents:
            response = client.post(
                "/documents/upload",
                data={"title": f"Evaluation J10 - {document.title}"},
                files={
                    "file": (
                        f"{document.id}.pdf",
                        make_pdf(document.pages),
                        "application/pdf",
                    )
                },
            )
            response.raise_for_status()
            document_id = response.json()["id"]
            created.append(document_id)
            report["documents"][document.id] = document_id
            save()
            chunks_by_document[document.id] = _prepare_document(client, document_id)
            print(f"Indexé : {document.id}", flush=True)
        for case in corpus.cases:
            result = _run_case(
                client,
                case,
                report["documents"][case.document_id],
                chunks_by_document[case.document_id],
            )
            report["results"].append(result)
            save()
            print(
                f"{case.id}: HTTP {result.get('http_status', 'réseau')} ; contrôles {result['issues'] or 'OK'}",
                flush=True,
            )
            if result.get("http_status") == 429:
                report["status"] = "quota_reached"
                break
        else:
            report["status"] = "completed"
    except (httpx.HTTPError, ValidationError, ValueError) as error:
        report["setup_error"] = type(error).__name__
        if isinstance(error, httpx.HTTPStatusError):
            report["setup_http_status"] = error.response.status_code
    finally:
        for document_id in created:
            try:
                response = client.delete(f"/documents/{document_id}")
                if response.status_code != 404:
                    response.raise_for_status()
            except httpx.HTTPError:
                report["cleanup_errors"].append(document_id)
        report["finished_at"] = datetime.now(UTC).isoformat()
        save()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://api:8000")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / f"rag-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex[:8]}.json",
    )
    args = parser.parse_args()
    with httpx.Client(
        base_url=args.api_url, timeout=180, follow_redirects=False
    ) as client:
        report = run_evaluation(client, args.report)
    print(f"Rapport à relire : {args.report}")
    return int(
        report["status"] != "completed"
        or bool(report["cleanup_errors"])
        or any(result["issues"] for result in report["results"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
