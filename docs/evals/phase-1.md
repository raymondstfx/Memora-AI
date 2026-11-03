# Phase 1 delivery and verification

Phase 2 continuation note (November 3, 2026): real-model acceptance is still
**pending verification**. No real Key was supplied or used during Phase 2.

Subsequent Gemini follow-up: the owner supplied local credentials and authorized
a bounded live smoke test. The requested `gemini-2.5-flash-lite` returned HTTP 404;
no live model gate passed. See [the Gemini report](gemini-compatibility.md).

Date: November 2, 2026 (Asia/Shanghai).

## Status and scope

Phase 1 implementation and credential-independent verification are complete.
**The real-provider acceptance gate remains pending owner-supplied credentials.**
No real external LLM call was made, and no simulated answer is exposed through
the normal application. At the original Phase 1 handoff, Phase 2 had not started
and no commit or push had been performed. The Phase 2 report records the subsequent
delivery and owner-authorized publication.

The authoritative private specification, AGENTS.md, existing implementation and
Phase 0 report were read before changes. The modular FastAPI/React/Postgres/Redis
architecture and baseline API paths are retained.

## Delivered changes

- `0002_chat` adds UUID-scoped users, conversations and messages with UTC times,
  explicit response states, sequence ordering, request deduplication and one active
  response per conversation. Frozen official checkpoint DDL is managed by Alembic.
- `backend/app/services/llm` implements a real OpenAI-compatible HTTP/SSE adapter.
  Settings are backend-only. Missing/placeholder credentials, invalid Base URLs,
  unsupported provider names, auth/network/timeout errors, malformed/empty streams,
  truncation, output limits and unexpected tool calls fail honestly.
- `backend/app/agents` implements a LangGraph completion node with the official
  Postgres saver, thread-offloaded async methods for Windows, bounded recent
  context and durable extractive excerpts. Outbound LangSmith tracing is disabled.
  Future tools have validated contracts but no registered executors.
- `backend/app/services/chat.py` owns message writes, ownership, deduplication,
  explicit retry, cancellation, partial-content persistence and restart recovery.
  User and pending assistant commit before provider invocation. Per-owner
  admission is serialized and defaults to two active responses across conversations.
- `/api/chat/stream`, `/api/conversations`, and ordered message history are live.
  Config, cancel and retry endpoints extend the contract. SSE and HTTP errors use
  the existing request-ID/error conventions. Model readiness is separate from
  infrastructure health.
- `frontend/src/features/chat` provides conversation creation/switching, URL-based
  selection restoration, token streaming, empty/loading/error/retry states, stop,
  failed-attempt history and clear missing-Key guidance. Text is never rendered as
  executable HTML. Nginx buffering/cache is disabled for SSE.
- `.env.example`, Compose injection, generated OpenAPI/TypeScript, README,
  contributor guidance, architecture/API docs and verification recipes are updated.

## Actual final verification

| Executed check | Result |
| --- | --- |
| `python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy on 23 source files, **25 unit/contract tests**; 8 integration cases deselected intentionally |
| `python -m pytest tests/integration/test_chat.py -q` on isolated real Postgres | PASS: earlier targeted run of 6 chat cases; the final complete suite below executes 7 expanded chat cases |
| `python scripts/test_phase1.py` | PASS: **8 integration tests + 9 Playwright tests**, full Linux container builds, actual dependency failure/recovery and restart persistence |
| `npm run check` | PASS: Prettier, strict TypeScript and generated-contract freshness |
| `npm run build` | PASS: Vite production bundle, also built inside Linux frontend image |
| `python -m pip check` | PASS: no broken requirements |
| `python scripts/export_openapi.py` / `npm run api:types` | PASS: runtime OpenAPI and checked-in client types synchronized |
| `docker compose --profile app up --build -d --wait` | PASS: normal local API/frontend/Postgres/Redis healthy, migration exits 0 |
| Actual normal-stack `/api/health` | PASS: HTTP 200; postgres/pgvector/schema/redis all ready |
| Actual normal-stack `/api/chat/config` | PASS: `configured:false`, missing Key/model named; no secret returned |
| Actual normal-stack keyless `POST /api/chat/stream` | PASS: HTTP 503 `LLM_NOT_CONFIGURED`, no invented answer |
| `git check-ignore .env` and private MD/PDF paths | PASS: secrets/local environment and private specifications remain excluded |
| `git diff --check` | PASS |
| `python scripts/verify_live_chat.py --help` | PASS: opt-in live verification and history-only modes available; **no live requests executed** |
| Normal keyless-stack Playwright run | PASS: 6 tests; 3 test-upstream chat cases explicitly skipped, separately passed in the full suite above |

Commands used `.venv\Scripts\python`, `npm.cmd`, and installed Edge's Chromium
engine on Windows. The isolated Compose run used:

```powershell
$env:BUILDKIT_NO_CLIENT_TOKEN = '1'
$env:PLAYWRIGHT_CHANNEL = 'msedge'
.venv\Scripts\python scripts/test_phase1.py
```

Its final saved output includes `8 passed`, `9 passed`, and
`PASS: Phase 1 keyless implementation acceptance (test upstream, not real API)`.
Raw output is retained in ignored `logs/phase-1-acceptance.log`; normal startup
output is in ignored `logs/phase-1-startup.log`. Screenshots were inspected and
are retained in ignored `frontend/test-results/`.

The test-only HTTP upstream is a separate host process with obvious
`Test fixture:` output and dummy credentials. It is excluded from production
images. There is no runtime fake-provider selection or fallback. HTTP transport
doubles are explicitly confined to unit/integration tests. Test containers,
volumes, upstream process and the additional disposable local test DB were
cleaned up. Normal development volumes were retained.

## Coverage and acceptance limits

| Acceptance area | Verified evidence | Remaining limit |
| --- | --- | --- |
| A01 streaming and persistence | Browser shows token fragments; persisted assistant matches; reload restores | Real external model unverified |
| A02 conversation separation | New/switch/reload browser flow and provider-context isolation | Fixed local demo identity only |
| A19 restart persistence | Completed chat survives API/Postgres restart; Postgres/Redis probes retain values | Real-provider message not yet produced |
| A20 ownership | Other server-derived test identity receives 404 on history, send, retry and cancel | Public login/multi-tenant auth not implemented |
| Failure honesty | Missing Key, 401, timeout, malformed/empty/truncated stream, tool request, output limits | Actual provider-specific failures not yet exercised |
| Cancellation/retry | Partial content survives stop/reload; retries keep one user message and preserve failed assistant | No automatic replay/resume of a billable call |
| Context/checkpoints | Bounded multilingual input, durable excerpts, actual Postgres checkpoints | No Phase 4 semantic memory or retrieval |
| Schema lifecycle | Upgrade → downgrade base → upgrade head; Alembic metadata drift check | Checkpoint table structure is managed by frozen DDL, not ORM autogeneration |

The 9 Playwright cases cover navigation/readiness, mobile shell, missing-Key
guidance, streaming/reload/conversation separation, failure/retry, cancellation,
split UTF-8/SSE frames and missing-terminal-event detection. Tests also verify
that user input exists in a separate committed DB connection when the provider
is called, repeated request IDs do not invoke it again, and partial/failed
assistant messages cannot become successful context.

Development fixes included strict request-state typing, compatibility with the
installed LangGraph saver, unbuffered Nginx SSE, frozen checkpoint migrations,
test assertion imports and conservative context accounting. Initial failed checks
were corrected; the table above reports the actual final passing runs.

Validated additions: LangGraph 1.2.19, checkpoint-postgres 3.2.0, checkpoint 4.3.1,
psycopg-pool 3.3.3, HTTPX 0.28.1, LangSmith 0.14.17. Existing Python/Node,
Postgres/pgvector/Redis and frontend versions remain documented in Phase 0 and the
updated lockfiles. No fixture PDF, ingestion, vector retrieval, web search, email
or presentation functionality was implemented in this phase.

## Where to configure credentials

Current root `.env` and `.env.example` use the same lines for required settings:

| Setting | File and line | What to enter |
| --- | --- | --- |
| Provider | `.env:17` | `openai_compatible` |
| Model | `.env:19` | An exact model ID available to your provider/account |
| API Key | `.env:21` | Paste the real Key after `LLM_API_KEY=` here only |
| Base URL | `.env:23` | Provider API root; default `https://api.openai.com/v1` |
| Token parameter | `.env:25` | `max_completion_tokens`, or provider-required `max_tokens` |

Do not put credentials in tracked `.env.example`, frontend code or `VITE_*`.
Optional limits/timeouts/retry variables are documented in the template. The
example uses blank/obvious placeholders; the actual `.env` remains ignored.

After configuration, recreate the API environment with:

```powershell
docker compose --profile app up --build -d --wait
```

Then open `http://localhost:5173`. For hybrid development, use the README's
dependency/venv/Vite commands and restart the local API after editing `.env`.

To complete the pending real-provider gate, run:

```powershell
.venv\Scripts\python scripts/verify_live_chat.py --run-live
```

This explicitly permits three potentially billed synthetic model requests. It
checks real SSE, saved history, same-conversation marker recall and a separate
conversation. After API/Postgres restart, use the printed conversation UUID:

```powershell
docker compose restart api postgres
docker compose --profile app up -d --wait
.venv\Scripts\python scripts/verify_live_chat.py --conversation <printed-uuid>
```

Also manually verify Stop and invalid-Key handling using the UI, restoring valid
settings and restarting afterward. Actual account/model access, provider-specific
compatibility, answer quality, latency, quota and billing remain **unverified**.
Passing test-upstream checks is not claimed as real-provider acceptance. Stop at
Phase 1; Phase 2 requires a separate owner instruction.
