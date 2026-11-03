import json
import os
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.db.session import build_engine
from app.services.documents import DocumentService
from app.services.embedding import OpenAIEmbeddingProvider
from tests.pdf_fixtures import vector


@pytest.fixture
def service(tmp_path):
    if os.environ.get("MEMORA_TEST_DATABASE_RESET") != "1":
        pytest.skip("Requires isolated real database")
    settings = Settings(
        rag_min_similarity=0,
        storage_root=tmp_path,
        embedding_model="fixture-model",
        embedding_dimensions=16,
        embedding_api_key=SecretStr("test-only-credential"),
    )
    assert "_test" in settings.database_url.get_secret_value()
    engine = build_engine(settings)

    def handler(request):
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": vector(value, body["dimensions"])}
                    for i, value in enumerate(body["input"])
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    documents = DocumentService(
        engine, settings, OpenAIEmbeddingProvider(settings, client)
    )
    documents.enqueue = lambda _: None
    yield documents, uuid4(), client
    documents.redis.close()
    client.close()
    engine.dispose()
