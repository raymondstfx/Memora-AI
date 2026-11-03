# Phase 1: chat and persisted sessions

Scope: streaming chat, conversation switching/history, demo ownership, provider
adapter, LangGraph orchestration/checkpoints, bounded context and honest errors.
No document ingestion or retrieval is implemented. Later tools have typed
contracts only and are unavailable to the model in this phase.

The backend reads `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` and
bounded timeout/context/output settings. Only an OpenAI-compatible Chat Completions
provider is enabled. No runtime fake-provider setting exists. A configuration
endpoint reports missing variable names but never their secret values. Keyless
startup, persisted history and health remain operational.

Alembic adds UUID-scoped users, conversations, messages with UTC timestamps,
message status/errors, client request deduplication and official Postgres-backed
LangGraph checkpoints. Single-user demo auth always derives the owner on the
server; callers cannot set an owner ID. Private deployment authentication is
outside this phase; services remain bound to loopback.

`POST /api/chat/stream` persists user and pending assistant before invoking the
provider. SSE sends `message_start`, `token`, `message_end`, `error`; reserved
tool/citation events exist in the typed contract but are never invented. Explicit
cancel and retry endpoints preserve partial responses and reuse the same user
message. Per-conversation locking prevents overlapping responses. Interrupted
streams are marked incomplete and never treated as successful context. Provider
retries are bounded and occur only before output. Recovery never automatically
replays a billable provider request.

The React chat UI restores the selected conversation from the URL, lists history,
streams safely as text, and offers new conversation, stop, retry and error states.
Nginx disables response buffering for SSE. Generation continues server-side
independently of browser read speed so disconnects can be recorded reliably.

Verification: schema/config/provider unit tests with deterministic HTTP transport,
real Postgres migrations and ownership/idempotency/cancel/restart integration,
Playwright keyless/config/history/retry flows plus a test-only fake HTTP provider
outside the production image. Real external model quality/access/latency remains
explicitly unverified until the owner supplies credentials and performs opt-in
verification. Stop after Phase 1; no automatic commit or push.
