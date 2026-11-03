# Phase 1 API contract

Historical Phase 1 snapshot. Phase 2 extends PDF attachments and citation/tool
events; see `phase-2.md` for the current document/RAG contract.

All paths below start with `/api`. The existing health contract is retained;
readiness now requires Alembic head `0002_chat`. Model configuration is separate
from infrastructure health: missing credentials do not prevent startup or access
to existing conversation history.

All errors use `code`, `message`, `request_id`, optional `details`, and an
`X-Request-ID` response header. Error text never includes keys, provider response
bodies or raw connection errors. Responses/types are generated from OpenAPI,
including the SSE `StreamEvent` component.

| Method | Path | Contract |
| --- | --- | --- |
| GET | `/chat/config` | `{configured, missing[], provider, model, message}`; never returns key or connection secrets |
| GET | `/conversations` | Owner-filtered conversations ordered by last message time |
| GET | `/conversations/{id}/messages` | Owner-filtered messages ordered by integer position; includes complete/failed/partial status |
| POST | `/chat/stream` | `{conversation_id?: UUID, message: string, request_id?: UUID, attachments?: []}` → SSE |
| POST | `/messages/{id}/retry` | `{request_id?: UUID}` → SSE; latest unsuccessful assistant only, no duplicate user message |
| POST | `/messages/{id}/cancel` | Idempotently marks owned streaming assistant cancelled; returns persisted message |

The server derives a fixed demo user identity. A caller cannot submit or override
`user_id`; another owner's resource IDs return 404. This is local demo auth, not
public authentication. Exactly one API process/replica is supported in this phase.

## Streaming and failures

User message and pending assistant are committed before any provider request.
`request_id` is the client's deduplication UUID, separate from the server's tracing
request ID. Reusing it returns 409 and does not initiate another model call.
Concurrent generation in the same conversation returns 409. A per-owner
concurrency cap (default two responses) bounds provider work;
exceeding the cap returns 429 `CHAT_LIMIT_REACHED`. Request validation
rejects blank/over-4000-character messages, unknown fields and nonempty attachments.

SSE frames have `event: <name>` and JSON `data`, separated by a blank line:

```text
event: message_start
data: {"event":"message_start","conversation_id":"uuid","message_id":"uuid","status":"streaming"}

event: token
data: {"event":"token","conversation_id":"uuid","message_id":"uuid","text":"Hello"}

event: message_end
data: {"event":"message_end","conversation_id":"uuid","message_id":"uuid","status":"complete"}
```

After headers are sent, failures use an SSE `error` frame with `code`, `message`,
`request_id`, and `status` (`failed` or `incomplete`). Before streaming, configuration
errors use HTTP 503 `LLM_NOT_CONFIGURED`. No placeholder assistant answer is stored.
Provider auth, network errors, malformed streams, refusals, truncation, tool
requests and output limits are explicit failures. A stream must have text, a
successful stop reason and `[DONE]` to count as complete.

Partial output is saved before token publication. Stop retains partial content.
Browser disconnect cancels generation and marks it interrupted; a new API process
recovers orphaned streaming rows on the next history/list request. A stale timeout
also releases abandoned rows. Reloaded pending history is polled until settled.
No replay, regeneration or billable request happens without an explicit send or
retry. Older failed attempts remain visible when retry adds a new assistant.

The provider has connect/read/total timeouts. Only HTTP 429/502/503/504 may be
retried, with capped exponential delay, before any token is exposed. Midstream
errors and timeouts are never automatically retried. Nginx buffering/cache is
disabled and heartbeat comments keep long streams open.

## Context, tools and checkpoints

Model input has a fixed system boundary, a bounded extractive summary labelled
as incomplete/untrusted, and recent complete turns. Conservative UTF-8-byte
accounting limits input independently of the output cap. Partial/failed assistant
messages are excluded. This summary is conversation context, not Phase 4 semantic
memory. The UI renders text without HTML interpretation.

LangGraph uses the official Postgres saver with async operations offloaded to
threads for Windows compatibility. Thread IDs are server-derived
`user_id:conversation_id`; checkpoint tables have no public access route. Alembic
owns frozen versioned DDL, with no runtime `setup()` or `create_all()`. Both graph
input/output checkpoints and message records survive process/container restart.

The five future tool names have validated contracts. No executors or tools are
advertised to the provider in Phase 1, and there is no `send_email` tool. Reserved
`tool_start`, `tool_result`, and `citation` event variants exist in the contract
but are not emitted as fabricated activity. No Phase 2 ingestion/retrieval runs.

Protocol references: [official OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[LangGraph custom streaming](https://docs.langchain.com/oss/python/langgraph/streaming).
LangSmith outbound tracing is explicitly disabled for chat runs. Logs contain
request/conversation/message IDs, status, output character count and duration;
they do not contain prompt/answer text or credentials.
