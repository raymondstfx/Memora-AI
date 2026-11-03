import asyncio
import json
import os
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select, text

from app.core.auth import get_current_user
from app.core.config import Settings
from app.db.models import Conversation, Message
from app.main import create_app
from app.services.llm.provider import OpenAICompatibleProvider

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    if os.environ.get("MEMORA_TEST_DATABASE_RESET") != "1":
        pytest.skip("Requires isolated migrated test database")
    config = Settings(
        llm_provider="openai_compatible",
        llm_api_key=SecretStr("test-only-credential"),
        llm_model="test-model",
    )
    assert (
        "_test" in config.database_url.get_secret_value()
        or "_isolated" in config.database_url.get_secret_value()
    )
    app = create_app(config)
    owner = uuid4()
    app.dependency_overrides[get_current_user] = lambda: owner
    calls = []

    def upstream(request):
        calls.append(json.loads(request.content))
        query = calls[-1]["messages"][-1]["content"]
        with app.state.engine.connect() as db:
            assert (
                db.scalar(
                    select(Message.id)
                    .where(
                        Message.user_id == owner,
                        Message.role == "user",
                        Message.content == query,
                    )
                    .limit(1)
                )
                is not None
            )
        if query == "FAIL":
            return httpx.Response(401, text="secret upstream data")
        pieces = ["你好", " persisted answer"]
        frames = "".join(
            "data: " + json.dumps({"choices": [{"delta": {"content": part}}]}) + "\n\n"
            for part in pieces
        )
        if query == "PARTIAL":
            return httpx.Response(200, text=frames)
        return httpx.Response(
            200,
            text=frames + 'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n",
        )

    with TestClient(app) as test:
        fake_http = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        app.state.chat.provider = OpenAICompatibleProvider(config, fake_http)
        yield test, app, owner, calls
        asyncio.run(fake_http.aclose())


def send(client, message, conversation=None, request_id=None):
    return client.post(
        "/api/chat/stream",
        json={
            "message": message,
            "conversation_id": conversation,
            "request_id": str(request_id or uuid4()),
        },
    )


def start(response):
    assert response.status_code == 200, response.text
    data = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    return data[0], data


def test_stream_persistence_context_dedup_and_ownership(client):
    test, app, owner, calls = client
    request_id = uuid4()
    first, frames = start(send(test, "Remember amber", request_id=request_id))
    assert [event["event"] for event in frames] == [
        "message_start",
        "token",
        "token",
        "message_end",
    ]
    cid = first["conversation_id"]
    history = test.get(f"/api/conversations/{cid}/messages").json()
    assert [row["role"] for row in history] == ["user", "assistant"]
    assert history[-1]["content"] == "你好 persisted answer"
    assert history[-1]["status"] == "complete"
    assert send(test, "Remember amber", request_id=request_id).status_code == 409
    assert len(calls) == 1
    start(send(test, "What did I say?", cid))
    assert any(item["content"] == "Remember amber" for item in calls[-1]["messages"])
    other, _ = start(send(test, "Separate conversation"))
    assert other["conversation_id"] != cid
    assert not any(
        item["content"] == "Remember amber" for item in calls[-1]["messages"]
    )
    with app.state.engine.connect() as db:
        assert (
            db.scalar(
                text("SELECT count(*) FROM checkpoints WHERE thread_id = :thread"),
                {"thread": f"{owner}:{cid}"},
            )
            > 0
        )
    app.dependency_overrides[get_current_user] = lambda: uuid4()
    assert test.get(f"/api/conversations/{cid}/messages").status_code == 404
    assert test.get("/api/conversations").json() == []
    assert send(test, "steal", cid).status_code == 404
    assert test.post(f"/api/messages/{first['message_id']}/cancel").status_code == 404
    assert (
        test.post(f"/api/messages/{first['message_id']}/retry", json={}).status_code
        == 404
    )


def test_failure_and_retry_preserve_one_user_message(client):
    test, app, _, calls = client
    first, frames = start(send(test, "FAIL"))
    assert frames[-1]["event"] == "error"
    assert frames[-1]["code"] == "PROVIDER_AUTH_ERROR"
    assert "secret upstream" not in json.dumps(frames)
    rows = test.get(f"/api/conversations/{first['conversation_id']}/messages").json()
    assert rows[-1]["content"] == "" and rows[-1]["status"] == "failed"
    retry = test.post(f"/api/messages/{first['message_id']}/retry", json={})
    start(retry)
    rows = test.get(f"/api/conversations/{first['conversation_id']}/messages").json()
    assert [r["role"] for r in rows] == ["user", "assistant", "assistant"]
    assert len(calls) == 2
    partial, frames = start(send(test, "PARTIAL"))
    assert frames[-1]["status"] == "incomplete"
    rows = test.get(f"/api/conversations/{partial['conversation_id']}/messages").json()
    assert rows[-1]["content"] and rows[-1]["status"] == "incomplete"
    partial_content = rows[-1]["content"]
    start(send(test, "Continue after interrupted answer", partial["conversation_id"]))
    assert not any(
        item["role"] == "assistant" and item["content"] == partial_content
        for item in calls[-1]["messages"]
    )


def test_restart_recovers_unfinished_and_busy_is_rejected(client):
    test, app, owner, _ = client
    chat = app.state.chat
    from app.schemas.chat import ChatRequest

    body = ChatRequest(message="pending", request_id=uuid4())
    turn = chat.prepare(owner, body, body.request_id)
    assert send(test, "parallel", str(turn.conversation_id)).status_code == 409
    chat.save(turn, "partial before crash")
    # New application instance = process restart, same real DB and checkpoints.
    fresh = create_app(chat.settings)
    fresh.dependency_overrides[get_current_user] = lambda: owner
    with TestClient(fresh) as restarted:
        rows = restarted.get(
            f"/api/conversations/{turn.conversation_id}/messages"
        ).json()
        assert rows[-1]["status"] == "interrupted"
        assert rows[-1]["content"] == "partial before crash"


def test_missing_key_is_actionable_without_persisting_fake_answer(client):
    test, app, _, calls = client
    app.state.chat.settings = app.state.chat.settings.model_copy(
        update={"llm_api_key": SecretStr("")}
    )
    assert not test.get("/api/chat/config").json()["configured"]
    response = send(test, "hello")
    assert response.status_code == 503
    assert response.json()["code"] == "LLM_NOT_CONFIGURED"
    assert "LLM_API_KEY" in response.json()["message"]
    assert calls == []
    assert test.get("/api/conversations").json() == []


def test_cancel_persists_partial_and_allows_retry(client):
    _, app, owner, _ = client
    chat = app.state.chat
    from app.schemas.chat import ChatRequest

    class Slow:
        async def stream(self, messages):
            yield "partial"
            await asyncio.sleep(60)

    chat.provider = Slow()
    body = ChatRequest(message="slow", request_id=uuid4())
    turn = chat.prepare(owner, body, body.request_id)

    async def exercise():
        events = chat.events(turn, "test-request")
        assert "message_start" in await anext(events)
        assert "token" in await anext(events)
        row = chat.cancel(owner, turn.message_id)
        assert row.status == "cancelled"
        chat.tasks[turn.message_id].cancel()
        await events.aclose()

    asyncio.run(exercise())
    rows = chat.history(owner, turn.conversation_id)
    assert rows[-1].content == "partial" and rows[-1].status == "cancelled"


def test_per_user_concurrency_is_bounded(client):
    test, app, owner, _ = client
    from app.schemas.chat import ChatRequest

    for _ in range(2):
        body = ChatRequest(message="pending", request_id=uuid4())
        app.state.chat.prepare(owner, body, body.request_id)
    response = send(test, "too many")
    assert response.status_code == 429
    assert response.json()["code"] == "CHAT_LIMIT_REACHED"


def test_bounded_summary_is_durable_in_postgres(client):
    test, app, _, calls = client
    app.state.chat.settings = app.state.chat.settings.model_copy(
        update={"llm_context_token_budget": 2048}
    )
    first, _ = start(send(test, "first detail " * 20))
    cid = first["conversation_id"]
    start(send(test, "second detail " * 20, cid))
    start(send(test, "third detail " * 20, cid))
    assert (
        sum(len(item["content"].encode()) + 32 for item in calls[-1]["messages"])
        <= 2048
    )
    with app.state.chat.sessions() as db:
        from uuid import UUID

        conversation = db.get(Conversation, UUID(cid))
        assert conversation.summary and conversation.summary_position > 0
