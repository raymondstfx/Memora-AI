import pytest

from app.services.pdf import extract_pages
from tests.pdf_fixtures import pdf_bytes

pytestmark = pytest.mark.integration


def test_failed_lease_cannot_resume_embedding_or_become_ready(service, monkeypatch):
    documents, owner, _ = service
    result = documents.upload(owner, "brief.pdf", "application/pdf", pdf_bytes())

    def expire(*args):
        documents.fail(result.job_id, "JOB_INTERRUPTED", "Test lease expired")
        return extract_pages(*args)

    monkeypatch.setattr("app.services.documents.extract_pages", expire)
    documents.ingest(result.job_id)
    detail = documents.detail(owner, result.document_id)
    assert detail.status == "failed" and detail.error_code == "JOB_INTERRUPTED"
