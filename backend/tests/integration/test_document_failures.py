from types import MethodType

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError

from app.core.auth import get_current_user
from app.main import create_app
from app.services.documents import DocumentService
from tests.integration.test_documents import upload
from tests.pdf_fixtures import pdf_bytes

pytestmark = pytest.mark.integration


def test_upload_type_header_size_limits(service):
    documents, owner, _ = service
    settings = documents.settings.model_copy(update={"pdf_max_upload_bytes": 1024})
    documents.settings = settings
    app = create_app(settings)
    app.dependency_overrides[get_current_user] = lambda: owner
    with TestClient(app) as client:
        app.state.documents = documents
        cases = [
            ("bad.txt", b"%PDF-test", "application/pdf", 415),
            ("bad.pdf", b"%PDF-test", "text/plain", 415),
            ("bad.pdf", b"hello", "application/pdf", 422),
            ("big.pdf", b"%PDF-" + b"x" * 2000, "application/pdf", 413),
            ("huge.pdf", b"%PDF-" + b"x" * 70000, "application/pdf", 413),
        ]
        for filename, data, mime, status in cases:
            result = client.post(
                "/api/documents/upload", files={"file": (filename, data, mime)}
            )
            assert result.status_code == status
            assert result.json()["request_id"] == result.headers["x-request-id"]
    assert documents.listing(owner) == []


def test_queue_failure_is_saved_not_ready(service, monkeypatch):
    documents, owner, _ = service
    documents.enqueue = MethodType(DocumentService.enqueue, documents)

    def unavailable(*args, **kwargs):
        raise ConnectionError("private connection detail")

    monkeypatch.setattr(documents.redis.connection_pool, "get_connection", unavailable)
    result = documents.upload(owner, "brief.pdf", "application/pdf", pdf_bytes())
    detail = documents.detail(owner, result.document_id)
    assert detail.status == "failed" and detail.error_code == "QUEUE_UNAVAILABLE"
    assert "private" not in detail.error_message


def test_injected_bad_vector_cannot_commit_success(service):
    documents, owner, _ = service

    class Bad:
        def embed(self, texts):
            return [[1, 2] for _ in texts]

    documents.embeddings = Bad()
    result = upload(documents, owner)
    detail = documents.detail(owner, result.document_id)
    assert (
        detail.status == "failed" and detail.error_code == "EMBEDDING_INVALID_RESPONSE"
    )
