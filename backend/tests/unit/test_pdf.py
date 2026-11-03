import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.schemas.documents import SourceCitation
from app.services.embedding import (
    OpenAIEmbeddingProvider,
    embedding_configuration,
    profile,
)
from app.services.llm.provider import ChatError
from app.services.pdf import chunk_pages, extract_pages, lexical_text
from app.services.rag import grounded_answer, validate_answer
from app.services.storage import PrivateStorage, safe_filename
from tests.pdf_fixtures import pdf_bytes


def configured(**kwargs):
    return Settings(
        _env_file=None,
        **{
            "embedding_model": "fixture-model",
            "embedding_dimensions": 8,
            "embedding_api_key": SecretStr("test-only-credential"),
            **kwargs,
        },
    )


def test_embedding_pair_and_profile_are_explicit():
    assert not embedding_configuration(Settings(_env_file=None)).configured
    first = configured()
    assert embedding_configuration(first).configured
    assert profile(first) != profile(configured(embedding_dimensions=16))
    assert profile(first) != profile(configured(embedding_model="different"))
    assert profile(first) == profile(
        configured(embedding_api_key=SecretStr("changed-key"))
    )


@pytest.mark.parametrize("vectors", [[1, 2], [0] * 8, [float("nan")] * 8])
def test_invalid_embedding_does_not_pass(vectors):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"data": [{"index": 0, "embedding": vectors}]}
            )
        )
    ) as client:
        with pytest.raises((ChatError, ValueError)):
            OpenAIEmbeddingProvider(configured(), client).embed(["hello"])


def test_embedding_reorders_indices_and_sends_dimension_pair():
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "fixture-model" and body["dimensions"] == 8
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [2] * 8},
                    {"index": 0, "embedding": [1] * 8},
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert OpenAIEmbeddingProvider(configured(), client).embed(["one", "two"]) == [
            [1] * 8,
            [2] * 8,
        ]


def test_embedding_missing_key_never_calls_transport():
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("No network allowed"))
    ) as client:
        with pytest.raises(ChatError, match="EMBEDDING_API_KEY"):
            OpenAIEmbeddingProvider(
                configured(embedding_api_key=SecretStr("")), client
            ).embed(["test"])


def test_chunks_overlap_preserve_page_and_hash():
    chunks = chunk_pages(
        [" ".join(f"word{i}" for i in range(70)), "第二页 PDF 引用测试"], 30, 5, 100
    )
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].text.split()[-5:] == chunks[1].text.split()[:5]
    assert chunks[-1].page_no == 2
    assert all(c.text_hash and c.token_count <= 30 for c in chunks)
    assert "第 二 页" in lexical_text("第二页")


def test_real_parser_and_unsupported_pages(tmp_path):
    path = tmp_path / "brief.pdf"
    path.write_bytes(pdf_bytes())
    pages = extract_pages(path, configured())
    assert len(pages) == 2 and "November 5, 2026" in pages[0]
    path.write_bytes(pdf_bytes(encrypted=True))
    with pytest.raises(ChatError, match="PDF_ENCRYPTED"):
        extract_pages(path, configured())
    with pytest.raises(ChatError, match="Page 2"):
        chunk_pages(["some text", ""], 600, 100, 100)


def test_private_paths_and_display_filename(tmp_path):
    storage = PrivateStorage(tmp_path)
    with pytest.raises(ChatError):
        storage.path("../outside")
    assert safe_filename("../../evil.pdf") == "evil.pdf"


def test_grounding_rejects_unknown_refs_and_repairs_only_once():
    source = SourceCitation(
        key="pdf:known",
        label=1,
        chunk_id=uuid4(),
        document_id=uuid4(),
        filename="brief.pdf",
        page_no=1,
        excerpt="API due November 5, 2026.",
        score=1,
    )
    answer, sources = validate_answer(
        json.dumps(
            {"answer": "API due November 5 [pdf:known]", "source_refs": ["pdf:known"]}
        ),
        [source],
    )
    assert "[1]" in answer and sources[0].filename == "brief.pdf"

    class Invalid:
        calls = 0

        async def stream(self, messages):
            self.calls += 1
            yield '{"answer":"made up [pdf:unknown]", "source_refs":["pdf:unknown"]}'

    provider = Invalid()
    with pytest.raises(ChatError, match="invalid grounding"):
        asyncio.run(grounded_answer(provider, "deadline?", [source], 12000))
    assert provider.calls == 2
