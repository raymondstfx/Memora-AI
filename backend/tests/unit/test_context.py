from app.agents.prompts import SYSTEM_PROMPT
from app.db.models import Message
from app.services.chat import bounded_context


def test_context_has_bounded_recent_turns_and_durable_excerpts():
    records = [
        Message(
            position=i,
            role="user" if i % 2 else "assistant",
            content="中文 evidence " * 30,
        )
        for i in range(1, 42)
    ]
    prompt, summary, position = bounded_context(records, "", 0, 4096)
    assert prompt[0]["content"] == SYSTEM_PROMPT
    assert prompt[-1]["content"] == records[-1].content
    assert sum(len(p["content"].encode()) + 32 for p in prompt) <= 4096
    assert summary and position > 0
    assert "untrusted" in prompt[1]["content"]
