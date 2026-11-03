import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.auth import get_current_user
from app.db.models import DocumentChunk, Job
from app.main import create_app
from app.services.embedding import OpenAIEmbeddingProvider
from app.services.llm.provider import ChatError, OpenAICompatibleProvider
from tests.pdf_fixtures import pdf_bytes

pytestmark = pytest.mark.integration


def upload(documents, owner, data=None, filename="project_brief.pdf"):
    result = documents.upload(owner, filename, "application/pdf", data or pdf_bytes())
    documents.ingest(result.job_id)
    return result


def test_pdf_ingest_hybrid_search_dedup_and_scope(service):
    documents, owner, _ = service
    data = pdf_bytes()
    result = upload(documents, owner, data)
    detail = documents.detail(owner, result.document_id)
    assert (
        detail.status == "ready" and detail.chunk_count == 2 and detail.page_count == 2
    )
    sources = documents.retrieve(owner, "API deadline", [result.document_id])
    assert sources and sources[0].page_no == 1
    assert sources[0].vector_rank and sources[0].text_rank
    assert "November 5, 2026" in sources[0].excerpt
    duplicate = documents.upload(owner, "duplicate.pdf", "application/pdf", data)
    assert duplicate.duplicate and duplicate.document_id == result.document_id
    documents.ingest(result.job_id)
    assert documents.job(owner, result.job_id).attempts == 1
    with pytest.raises(ChatError) as error:
        documents.retrieve(uuid4(), "API", [result.document_id])
    assert error.value.status == 404
    assert documents.listing(uuid4()) == []


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"%PDF-corrupt", "PDF_CORRUPT"),
        (pdf_bytes([""]), "PDF_OCR_REQUIRED"),
        (pdf_bytes(["text", ""]), "PDF_OCR_REQUIRED"),
        (pdf_bytes(encrypted=True), "PDF_ENCRYPTED"),
    ],
)
def test_unsupported_never_becomes_ready(service, data, expected):
    documents, owner, _ = service
    result = upload(documents, owner, data)
    detail = documents.detail(owner, result.document_id)
    assert detail.status == "failed" and detail.error_code == expected
    assert documents.job(owner, result.job_id).status == "failed"


def test_missing_embedding_key_preserves_parse_and_retry_reuses_chunks(
    service, monkeypatch
):
    documents, owner, client = service
    valid = documents.settings
    documents.settings = valid.model_copy(update={"embedding_api_key": SecretStr("")})
    documents.embeddings = OpenAIEmbeddingProvider(documents.settings, client)
    result = upload(documents, owner)
    detail = documents.detail(owner, result.document_id)
    assert detail.status == "failed" and detail.error_code == "EMBEDDING_NOT_CONFIGURED"
    assert detail.extracted and detail.chunk_count == 2
    monkeypatch.setattr(
        "app.services.documents.extract_pages",
        lambda *_: pytest.fail("Extraction should be cached"),
    )
    documents.settings = valid
    documents.embeddings = OpenAIEmbeddingProvider(valid, client)
    retry = documents.reprocess(owner, result.document_id, False, False)
    documents.ingest(retry.job_id)
    assert documents.detail(owner, result.document_id).status == "ready"


def test_profile_change_requires_explicit_reindex_and_deletion_cascades(service):
    documents, owner, client = service
    result = upload(documents, owner)
    documents.settings = documents.settings.model_copy(
        update={"embedding_dimensions": 32, "embedding_model": "fixture-model-v2"}
    )
    documents.embeddings = OpenAIEmbeddingProvider(documents.settings, client)
    assert documents.detail(owner, result.document_id).status == "needs_reindex"
    with pytest.raises(ChatError, match="explicit reindex"):
        documents.retrieve(owner, "API deadline", [result.document_id])
    retry = documents.reprocess(owner, result.document_id, True, False)
    documents.ingest(retry.job_id)
    assert documents.detail(owner, result.document_id).embedding_dimensions == 32
    assert documents.retrieve(owner, "API deadline", [result.document_id])
    with documents.sessions() as db:
        original = documents.owned(db, owner, result.document_id).storage_key
    documents.remove(owner, result.document_id)
    assert not documents.storage.path(original).exists()
    with documents.sessions() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(DocumentChunk)
                .where(DocumentChunk.document_id == result.document_id)
            )
            == 0
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(Job)
                .where(Job.target_id == result.document_id)
            )
            == 0
        )


def test_api_grounding_citations_persist_and_ownership(service):
    documents, owner, _ = service
    result = upload(documents, owner)
    settings = documents.settings.model_copy(
        update={
            "llm_api_key": SecretStr("test-only-credential"),
            "llm_model": "fixture-chat",
            "llm_provider": "openai_compatible",
        }
    )
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: owner

    def handler(request):
        payload = json.loads(json.loads(request.content)["messages"][-1]["content"])
        source = payload["evidence"][0]
        content = json.dumps(
            {
                "answer": "The API deadline is November 5, 2026 ["
                + source["key"]
                + "]",
                "source_refs": [source["key"]],
            }
        )
        return httpx.Response(
            200,
            text="data: "
            + json.dumps({"choices": [{"delta": {"content": content}}]})
            + '\n\ndata: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n",
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with TestClient(app) as api:
        app.state.chat.provider = OpenAICompatibleProvider(settings, client)
        app.state.chat.documents = documents
        response = api.post(
            "/api/chat/stream",
            json={"message": "API deadline?", "attachments": [str(result.document_id)]},
        )
        assert response.status_code == 200
        frames = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert frames[-1]["event"] == "message_end", frames
        assert any(frame["event"] == "citation" for frame in frames)
        cid = frames[0]["conversation_id"]
        history = api.get(f"/api/conversations/{cid}/messages").json()
        assert "[1]" in history[-1]["content"]
        assert history[-1]["citations_json"][0]["filename"] == "project_brief.pdf"
        assert api.get(f"/api/documents/{result.document_id}/file").status_code == 200
        app.dependency_overrides[get_current_user] = lambda: uuid4()
        for path in [
            f"/api/documents/{result.document_id}",
            f"/api/documents/{result.document_id}/file",
            f"/api/jobs/{result.job_id}",
        ]:
            assert api.get(path).status_code == 404
    asyncio.run(client.aclose())
