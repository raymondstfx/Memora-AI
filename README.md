# Memora AI

**A connected workspace for information, understanding, and action.**

Memora AI is being built as a local-first AI knowledge workspace, bringing
conversations, document evidence, meeting insights, durable memory, approved
actions, and editable presentations into one place.

**Current implementation: Phase 2 — PDF ingestion and grounded retrieval.**
Chat streams through a backend provider adapter, saves conversations and partial
responses in Postgres, and restores history on reload/restart. LangGraph
checkpoints persist server-side. Missing credentials produce a configuration
notice; there are no simulated production answers. Real external API acceptance
has passed a bounded Gemini streaming/RAG smoke test. PDF upload, asynchronous parsing/indexing,
hybrid retrieval and page citations are implemented. Meetings, durable semantic
memory, email, web search and presentations belong to later phases. Both real
Phase 1 model and Phase 2 full RAG acceptance remain pending verification.
The Gemini follow-up verified real 768-dimensional embeddings and hybrid retrieval
on a tiny PDF. The subsequent 404 fix selected `gemini-3.1-flash-lite` from the
official model list and passed streaming plus a page-verified RAG answer. See
[the model-resolution report](docs/evals/gemini-model-resolution.md).

## Architecture

```text
React + TypeScript + Vite + Tailwind
                 │ same-origin /api proxy
             FastAPI / Pydantic v2
                 ├── PostgreSQL + pgvector
                 └── Redis
             SQLAlchemy 2 + Alembic
             LangGraph + Postgres checkpoints
                 └── configured OpenAI-compatible chat provider
```

The backend is a modular monolith. Future agent workflows and provider adapters
will call application services; email dispatch will require explicit approval.
The UI never represents placeholders as working AI functionality.

## Prerequisites

- Docker Engine / Docker Desktop with Linux containers and Docker Compose v2+.
- For hybrid development and local checks: Python 3.13+, Node.js 22.12+ and npm.
- Free default ports: `5432`, `6379`, `8000`, `5173`.

Exact Python dependencies are recorded in `backend/requirements*.lock`; frontend
dependencies in `frontend/package-lock.json`. Tested versions and gate evidence
are recorded in [the Phase 2 report](docs/evals/phase-2.md), with the original
[Phase 0 baseline](docs/evals/phase-0.md) preserved.

## Quick start: all containers

Copy the configuration once:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux, use `cp .env.example .env`. Then start the complete stack:

```sh
docker compose --profile app up --build -d --wait
```

Open [the workspace](http://localhost:5173), [API documentation](http://localhost:8000/docs),
or [dependency health](http://localhost:8000/api/health).

Compose waits for Postgres, applies Alembic migrations, and then starts the API
and frontend. Health returns `200` only when Postgres, pgvector, the expected
schema revision, and Redis are ready. An unavailable dependency returns `503`
with a request ID and dependency states. The UI supports refresh and retry.

The default database credentials are for local development. Published ports bind
to loopback. A fixed server-side demo identity scopes chat records; there is no
public login or tenant administration. Run exactly one API process/replica.
Provider credentials are optional for startup/history but required for answers.

## Configure a real chat provider

Edit the ignored root `.env`, **not** frontend code or `.env.example`. The template
has comments and empty/obvious placeholders:

```dotenv
LLM_PROVIDER=openai_compatible
LLM_MODEL=gemini-3.1-flash-lite
LLM_API_KEY=
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_TOKEN_PARAMETER=max_tokens
LLM_REASONING_EFFORT=minimal
```

Paste your Key after `LLM_API_KEY=` and replace `LLM_MODEL` with a model ID that
your provider/account actually supports. Base URL is the API root, including
`/v1` where required, without `/chat/completions`. Other providers may need
`LLM_TOKEN_PARAMETER=max_tokens`. Timeout, output and input-budget limits are
documented alongside these variables. Unsupported providers and empty/placeholder
values are reported by `GET /api/chat/config`. This endpoint never returns the
Key. Infrastructure health does not depend on model access.

Compose injects these variables only on the backend. After editing `.env`:

```sh
docker compose --profile app up --build -d --wait
```

For hybrid development, stop and restart the local API process after changing
`.env`. Do not overwrite a populated `.env` by copying the template again. Never
use `VITE_*` for API credentials. User messages go to your configured model
provider when you explicitly send or retry. Chat content is rendered as text.

The checked-in template now targets Gemini's official OpenAI-compatible endpoint,
with `gemini-3.1-flash-lite`, minimum supported thinking via the actual JSON field
`reasoning_effort: "minimal"` (not disabled), and `gemini-embedding-001` requested at 768 dimensions.
Set both backend Key variables locally (the same Gemini Key can be used for both).
See [Gemini setup and measured verification](docs/evals/gemini-compatibility.md).

## Verify with your real API credentials

The optional `scripts/verify_live_*.py` tools below are retained only in the
owner's local workspace. They are not distributed in a fresh public checkout;
manual browser verification remains available without them.

1. Open `http://localhost:5173`; the configuration notice should disappear.
2. Send a question and observe streamed text, then reload. Create another
   conversation and switch back; histories should remain separate.
3. Use **Stop response** during generation. The partial response should remain
   marked cancelled. Test invalid credentials: expect an explicit error and no
   fabricated assistant answer. Restore credentials and restart the API.
4. Optionally run the opt-in smoke script, which makes three potentially billed
   model requests using synthetic prompts and verifies streaming/history/context:

```sh
python scripts/verify_live_chat.py --run-live
```

It prints a conversation UUID. After restarting containers, verify its persisted
history without making another model call:

```sh
docker compose restart api postgres
docker compose --profile app up -d --wait
python scripts/verify_live_chat.py --conversation <printed-uuid>
```

The live script was **not run with real credentials** during this delivery.
Provider availability, account/model permissions, real response quality, latency
and billing remain unverified. [The Phase 1 report](docs/evals/phase-1.md) separates
test-upstream evidence from the pending real-credential gate.

```sh
docker compose --profile app ps
docker compose --profile app logs --tail 50 api migrate
docker compose --profile app down
```

`down` retains named Postgres and Redis volumes. Avoid `down --volumes` on your
development stack unless you intend to erase its data.

## Hybrid development: local API and UI, container dependencies

Start all dependencies with one command:

```sh
docker compose --profile app stop api frontend worker
docker compose -f docker-compose.yml -f docker-compose.hybrid.yml --profile app up --build -d --wait postgres redis migrate worker
```

Create and activate a Python environment, then install locked dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.lock
python scripts/dev.py migrate
python scripts/dev.py api
```

If PowerShell activation is blocked, invoke `.venv\Scripts\python.exe` directly
in place of `python`; no execution-policy changes are necessary. On macOS/Linux,
activate with `source .venv/bin/activate`.

In a second terminal:

```sh
cd frontend
npm ci
npm run dev
```

On Windows, use `npm.cmd` if PowerShell blocks `npm.ps1`. Vite proxies `/api` to
`http://127.0.0.1:8000`; keys and database credentials stay on the backend. The
backend reads the root `.env` regardless of the working directory. Compose uses
service names internally and overrides the host connection URLs automatically.

For custom ports, change the `*_PORT` variables in `.env` and update host URLs
(`DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS`) accordingly. For a local API on a
different port, set `API_PROXY_TARGET` in the frontend terminal; run Vite with
`npm run dev -- --port <port>` and Uvicorn directly with `--port <port>`. Compose
constructs container database credentials from `POSTGRES_*`; percent-encode URL
reserved characters in passwords, or use URL-safe local credentials.

## Verification

At the owner's request, test source directories, synthetic test providers and
test/live-verification runners are excluded from the public branch and retained
locally. The test commands and results in this guide and historical reports
describe that local verification workspace. A fresh public checkout does not
contain these suites; `scripts/dev.py check` requires those local test sources
for its pytest step. Frontend `npm run check` / `npm run build`, backend Ruff/mypy,
API schema generation and normal application startup remain available.

With the repository virtual environment active, from the root:

```sh
python scripts/dev.py check
python scripts/dev.py export-api
cd frontend
npm ci
npm run check
npm run build
npx playwright install chromium
cd ..
python scripts/test_phase2.py
```

The Phase 2 acceptance runner creates an isolated Compose project named
`memora-phase2-test`, uses ports `55432`, `56379`, `58000`, `55173`, and removes
only that test project's containers and volumes afterward. It builds the full
stack, runs real migration upgrade/downgrade/upgrade checks, exercises pgvector,
checks direct and proxied health, tests dependency failure and recovery, verifies
Postgres/Redis data and complete chats across API/database restart, and runs
Playwright browser tests. A separate test-only HTTP provider runs temporarily
on port `58901`, with unmistakable `Test fixture:` output and dummy credentials.
It is excluded from production images and has no runtime provider-selection flag.
No real provider Key is needed or used for this suite. Do not run
multiple copies concurrently. The migration test requires an explicit reset flag
that the runner sets only for the isolated test database.

The browser suite checks navigation, readiness, chat streaming, reload/switching,
failure/retry, cancellation, missing-Key guidance and mobile layout. Unit tests
use explicit dependency doubles; integration tests use actual Postgres and Redis.
The older `scripts/test_infrastructure.py` remains a keyless baseline; it skips
browser cases that explicitly require the Phase 1 test upstream.

To use an already installed Chrome or Edge instead of downloading Chromium, set
`PLAYWRIGHT_CHANNEL=chrome` or `PLAYWRIGHT_CHANNEL=msedge` in the test terminal.

After changing API schemas, export OpenAPI and regenerate the checked-in client
types:

```sh
python scripts/dev.py export-api
cd frontend
npm run api:types
```

`npm run check` rejects stale generated types. See [the API contract](docs/api/phase-0.md)
and [implementation plan](docs/architecture/phase-0-plan.md).

## Repository guide

| Path | Responsibility |
| --- | --- |
| `frontend/src/app` | Workspace navigation and shell |
| `frontend/src/components` | Owned UI primitives |
| `frontend/src/features/health` | Live readiness panel |
| `frontend/src/features/chat` | Conversations, SSE, stop/retry and history |
| `frontend/src/types` | Generated API types |
| `backend/app/api` | REST routes |
| `backend/app/core` | Configuration, logging, error boundaries |
| `backend/app/db` | SQLAlchemy metadata and session factory |
| `backend/app/schemas` | Validated public API responses |
| `backend/app/agents` | LangGraph completion, checkpoint adapter and future tool contracts |
| `backend/app/services` | Scoped chat and LLM provider adapter |
| `backend/alembic` | Versioned database migrations |
| `backend/tests` | Local-only unit/infrastructure tests; excluded from public branch |
| `scripts` | Portable dev and acceptance commands |
| `docs` | Architecture, API contract and verification evidence |

## PDF knowledge and Embedding configuration

Open Knowledge Base and upload a text-based PDF. A real RQ worker validates,
parses by page, normalizes/chunks, embeds, and atomically publishes the index.
Track stages/progress and errors, use **Retry processing** to reuse extracted
chunks or **Reparse from PDF** to repeat extraction. Duplicate uploads reuse the
existing document/job. Missing Embedding configuration produces a failed job with
an explicit configuration error, never a ready index or mock vectors.

Edit the ignored root `.env` (line numbers refer to the current template):

| Variable | Line | Value |
| --- | --- | --- |
| `LLM_MODEL` | 19 | Exact chat model ID |
| `LLM_API_KEY` | 21 | Your real LLM Key |
| `LLM_BASE_URL` | 23 | Chat API root |
| `EMBEDDING_API_KEY` | 38 | Separate Embedding Key |
| `EMBEDDING_BASE_URL` | 40 | Embedding API root, without `/embeddings` |
| `EMBEDDING_MODEL` | 43 | Exact Embedding model ID |
| `EMBEDDING_DIMENSIONS` | 44 | Gemini requests 768; actual returned length must match |
| `EMBEDDING_SEND_DIMENSIONS` | 47 | False if provider does not accept this request field |

Gemini-specific controls in the same root `.env` / `.env.example`:

| Setting | Line | Effect |
| --- | --- | --- |
| `LLM_TOKEN_PARAMETER` | 25 | Sends `max_tokens` |
| `LLM_MAX_CONCURRENT_REQUESTS` | 35 | One active chat call per supported API process |
| `EMBEDDING_BATCH_SIZE` | 50 | Up to 8 strings in each `input` array |
| `LLM_REASONING_EFFORT` | 73 | Sends `minimal` for Gemini 3.1 Flash-Lite; do not use `none` |
| `PROVIDER_RETRY_MAX_WAIT_SECONDS` | 75 | At most 15 seconds per retry; longer server hints stop |
| `EMBEDDING_NORMALIZE` | 77 | Client-side L2 normalization; changes index identity |
| `EMBEDDING_MAX_INPUT_BYTES` | 80 | Conservative chunk/query byte guard, not a wire parameter |
| `EMBEDDING_MAX_CONCURRENT_REQUESTS` | 82 | Redis slots shared by API and workers |
| `EMBEDDING_MIN_INTERVAL_SECONDS` | 84 | Four-second spacing for uncached calls |
| `EMBEDDING_CACHE_TTL_SECONDS` | 86 | Private profile-scoped vectors cached for 24 hours |

RPM/TPM/RPD are project/model limits; batching and serialization do not guarantee
free quota availability. Inspect your actual AI Studio limits. HTTP 429 is
classified as daily quota, unavailable quota/billing, token rate, request rate or
unknown. Daily/zero quota is not retried. `Retry-After` (seconds/date) and Google's
`RetryInfo.retryDelay` are honored only within the configured wait and retry
count; unknown 429 without a timing hint stops. No partial stream is replayed.
No job or index is automatically resubmitted after failure.

The database currently uses exact pgvector cosine search and a GIN full-text
index, without HNSW/IVFFlat. The `vector` storage limit is 16,000 dimensions;
ordinary vector ANN indexes support up to 2,000. The 768-dimensional profile fits
both. Returned vectors must already match 768; the application never silently
truncates 3,072-dimensional replies. Switching model, dimensions, Base URL or
normalization requires an explicit rebuild. Existing oversized chunks need
`scripts/reindex_documents.py --document <uuid> --reparse`, not automatic retries.

Successful batches are cached even if a later batch fails. A retry reuses parsed
chunks and matching vectors; a profile change cannot reuse the old vectors.
Cache keys contain hashes, not raw PDF/query text. Document vectors are scoped to
owner/document and purged on deletion; query vectors expire after the TTL.

Model and dimensions must be configured together. The adapter validates every
returned vector. Keys remain server-side; no Key is automatically borrowed from
another provider setting. `.env.example` contains placeholders/comments only.
After editing configuration, recreate **both API and worker**:

```sh
docker compose --profile app up --build -d --wait
```

Select ready PDFs in Chat or click **Ask this PDF**. Source cards identify the
filename, page and evidence excerpt and link to the authorized original page.
RAG answers wait for grounding/citation validation before publishing text; plain
chat retains upstream token streaming. Unsupported/insufficient evidence is
reported honestly. No OCR is implemented; encrypted/corrupt and textless pages
require review. Chunk counts are approximate English-word/CJK token units.

## Changing the Embedding model or vector dimension

Indexes carry a fingerprint of provider, Base URL, model and dimensions. Changing
any of these makes old indexes **needs_reindex**. Searches reject mismatched
selected indexes rather than mixing incompatible vectors. Key rotation alone
preserves the profile. After changing `.env` and restarting API/worker, choose
**Rebuild index** in Knowledge Base or explicitly enqueue rebuilds:

```sh
python scripts/reindex_documents.py --all
# Or rebuild just one owned document:
python scripts/reindex_documents.py --document <document-uuid>
```

Cached text/chunks are reused; `--reparse` explicitly reparses the original PDF.
Old vectors are invalidated before rebuild; a failed job remains unavailable for
retrieval. Check job status until ready: enqueueing is not success. No schema
change is needed for a dimension change because vectors are profile-filtered
before exact distance calculations. Rebuilds make real Embedding calls only when
you configure real credentials and explicitly enqueue them.

The hybrid recipe above runs API/Vite locally and the RQ worker in Docker with
`docker-compose.hybrid.yml`, sharing `./data/private`. Do not run a named-volume
worker against host-local file paths. An alternative native worker command is
`python scripts/dev.py worker`; Windows selects RQ SimpleWorker. The container
worker is the verified path. Local provider URLs must be reachable from both API
and worker, with matching profiles. Upload defaults are 20 MiB/100 pages; if you
raise the application cap, also update Nginx `client_max_body_size`.

## Phase 2 verification and pending live gates

`python scripts/test_phase2.py` uses real Postgres/pgvector/GIN, Redis/RQ, native
PDF parsing and browsers, with independent test-only HTTP Embedding/LLM fixtures.
It tests original PDF/vector persistence across API/database/worker restart and
cleans its isolated project/volumes. Production images exclude all test providers.
Fixtures live under ignored `data/phase2-fixtures/`. This is not a real-provider
acceptance pass.

**Phase 1 real chat model: pending. Phase 2 full RAG: pending.** Real Gemini
Embedding dimensions/storage/retrieval passed a tiny synthetic-PDF smoke test;
a subsequent switch to `gemini-3.1-flash-lite` passed one real streaming chat and
one grounded answer with page-1 evidence. This bounded smoke does not replace
full live persistence/cancellation/restart acceptance. For additional owner-approved
verification, upload the
generated project brief (or your own known
PDF), wait for ready, ask its API deadline and check filename/page/excerpt against
the original. Reload, restart containers, repeat retrieval, then test a model or
dimension change followed by explicit rebuild. Invalid Key/dimensions and
corrupt/scanned files must fail without fabricated answers. Actual provider
access and grounded answer quality still require verification. The small
Embedding result does not establish corpus-wide semantic quality. See
[the Phase 2 report](docs/evals/phase-2.md) and
[the Gemini follow-up](docs/evals/gemini-compatibility.md).

## Configuration and privacy

`.env.example` documents chat configuration and reserved later-phase variables.
Search and SMTP settings are unused. PDF text is sent to configured Embedding
and LLM providers only during explicit indexing/query actions. RQ PDF ingestion
runs in its own worker; presentation/meeting workers are unavailable. Private
specifications, `.env` files, secrets,
dependencies, caches and runtime data are excluded from Git and Docker contexts.
Structured API logs include request IDs, status and duration without request
bodies, credentials or raw dependency exceptions.

## Troubleshooting

- **Docker cannot connect:** start Docker Desktop and select Linux containers.
- **Registry TLS timeout:** verify Docker's network/proxy settings and retry the
  failed image pull. If pulls succeed but BuildKit's client-side token fetch
  fails, set `BUILDKIT_NO_CLIENT_TOKEN=1` in the build terminal to let the daemon
  obtain the token. This does not disable TLS or authentication. See the
  [BuildKit maintainers' guidance](https://github.com/moby/buildkit/issues/4725).
  A valid Compose file alone does not prove startup passed.
- **Health shows 503:** inspect dependency states, `docker compose ps`, and API
  logs. In hybrid mode run `python scripts/dev.py migrate` after Postgres starts.
- **Database authentication fails after editing `.env`:** Postgres initialization
  variables apply only to a new volume. Use the original credentials or change
  the existing role password deliberately; do not erase valuable volumes.
- **Port already allocated:** change the documented port settings or stop the
  conflicting service. The isolated test ports must also be free.

## Delivery roadmap

0. Skeleton and local infrastructure — delivered.
1. Streaming chat and persisted sessions — implemented; real API gate pending Key.
2. PDF ingestion and grounded retrieval — implemented; real Embedding/RAG gate pending.
3. Meeting intelligence, tasks, and approved email.
4. Durable, time-aware memory.
5. Live search and PowerPoint generation.
6. Hardening and complete demonstration.

Development stops at each phase gate for owner approval. See [AGENTS.md](AGENTS.md)
for contributor commands and migration discipline. The owner authorized publishing
the completed Phase 1/2 work; Phase 3 still requires separate approval.
See [the Phase 2 API contract](docs/api/phase-2.md).
