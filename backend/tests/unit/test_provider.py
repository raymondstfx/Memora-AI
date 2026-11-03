import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from app.agents.tools import ToolRequest
from app.core.config import Settings
from app.schemas.chat import ChatRequest
from app.services.llm.provider import ChatError, OpenAICompatibleProvider, configuration


def settings(**changes):
    return Settings(
        _env_file=None,
        **{
            "llm_provider": "openai_compatible",
            "llm_model": "test-model",
            "llm_api_key": SecretStr("test-only-credential"),
            **changes,
        },
    )


def frame(content=None, finish=None):
    return (
        "data: "
        + json.dumps(
            {"choices": [{"delta": {"content": content}, "finish_reason": finish}]}
        )
        + "\n\n"
    )


def collect(handler, config=None):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return [
                token
                async for token in OpenAICompatibleProvider(
                    config or settings(), client
                ).stream([{"role": "user", "content": "test"}])
            ]

    return asyncio.run(run())


def test_streams_unicode_and_sends_only_configured_fields():
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["stream"] is True
        assert body["max_completion_tokens"] == 1024
        assert "tools" not in body
        assert request.headers["Authorization"] == "Bearer test-only-credential"
        return httpx.Response(
            200,
            text=frame("你好")
            + frame(" world")
            + frame(finish="stop")
            + "data: [DONE]\n\n",
        )

    assert collect(handler) == ["你好", " world"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("data: not-json\n\n", "PROVIDER_INVALID_RESPONSE"),
        (frame("partial"), "PROVIDER_INCOMPLETE"),
        (
            frame("partial") + frame(finish="length") + "data: [DONE]\n\n",
            "OUTPUT_LIMIT",
        ),
        (frame(finish="stop") + "data: [DONE]\n\n", "PROVIDER_INCOMPLETE"),
        (
            'data: {"choices":[{"delta":{"tool_calls":[{"name":"send_email"}]}}]}\n\n',
            "TOOLS_UNAVAILABLE",
        ),
    ],
)
def test_failures_never_become_success(body, code):
    with pytest.raises(ChatError) as error:
        collect(lambda _: httpx.Response(200, text=body))
    assert error.value.code == code


def test_auth_error_redacts_provider_body():
    with pytest.raises(ChatError) as error:
        collect(lambda _: httpx.Response(401, text="private upstream details"))
    assert error.value.code == "PROVIDER_AUTH_ERROR"
    assert "private" not in str(error.value)


def test_timeout_is_actionable():
    def handler(request):
        raise httpx.ReadTimeout("upstream secret", request=request)

    with pytest.raises(ChatError, match="timed out"):
        collect(handler)


def test_retry_is_bounded_before_output():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(ChatError):
        collect(handler)
    assert len(calls) == 2


def test_missing_key_does_not_touch_network():
    config = settings(llm_api_key=SecretStr(""))
    assert configuration(config).missing == ["LLM_API_KEY"]
    with pytest.raises(ChatError, match="LLM_API_KEY"):
        collect(lambda _: pytest.fail("Network must not be called"), config)


def test_schema_rejects_blank_attachments_and_owner_override():
    for body in [
        {"message": " "},
        {"message": "hi", "attachments": ["not-a-uuid"]},
        {"message": "hi", "user_id": "other"},
    ]:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate(body)
    with pytest.raises(ValidationError):
        ToolRequest(name="send_email", arguments={})


def test_configuration_rejects_secret_urls_and_unsupported_provider():
    assert not configuration(
        settings(llm_base_url="https://user:secret@example.com/v1")
    ).configured
    assert not configuration(settings(llm_provider="fake")).configured


def test_legacy_token_parameter_is_supported():
    def handler(request):
        body = json.loads(request.content)
        assert "max_tokens" in body and "max_completion_tokens" not in body
        return httpx.Response(
            200, text=frame("ok") + frame(finish="stop") + "data: [DONE]\n\n"
        )

    assert collect(handler, settings(llm_token_parameter="max_tokens")) == ["ok"]
