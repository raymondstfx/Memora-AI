# Memora AI

**A connected workspace for information, understanding, and action.**

Memora AI is being built as a local-first AI knowledge workspace, bringing
conversations, document evidence, meeting insights, durable memory, approved
actions, and editable presentations into one place.

**Current release: Phase 0 — skeleton and local infrastructure.** The repository
contains a working infrastructure API and a responsive navigation shell. Chat,
uploads, meeting analysis, memory, email, web search, and presentation generation
are planned features and are not implemented in this release.

## Architecture

```text
React + TypeScript + Vite + Tailwind
                 │ same-origin /api proxy
             FastAPI / Pydantic v2
                 ├── PostgreSQL + pgvector
                 └── Redis
             SQLAlchemy 2 + Alembic
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
are recorded in [the Phase 0 report](docs/evals/phase-0.md).

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

The default credentials are for local development. Published ports bind to
loopback. This release has no application authentication and is not ready for
public deployment. No external provider credentials are required for Phase 0.

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
docker compose up -d --wait postgres redis
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
python scripts/test_infrastructure.py
```

The infrastructure acceptance runner creates an isolated Compose project named
`memora-phase0-test`, uses ports `55432`, `56379`, `58000`, `55173`, and removes
only that test project's containers and volumes afterward. It builds the full
stack, runs real migration upgrade/downgrade/upgrade checks, exercises pgvector,
checks direct and proxied health, tests dependency failure and recovery, verifies
Postgres/Redis data across restart, and runs Playwright browser tests. Do not run
multiple copies concurrently. The migration test requires an explicit reset flag
that the runner sets only for the isolated test database.

The browser suite checks navigation, real API readiness, error/retry behavior,
and mobile layout. Browser error-state injection is confined to tests. Unit tests
use dependency doubles; integration tests use actual Postgres and Redis.

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
| `frontend/src/types` | Generated API types |
| `backend/app/api` | REST routes |
| `backend/app/core` | Configuration, logging, error boundaries |
| `backend/app/db` | SQLAlchemy metadata and session factory |
| `backend/app/schemas` | Validated public API responses |
| `backend/alembic` | Versioned database migrations |
| `backend/tests` | Unit and real infrastructure tests |
| `scripts` | Portable dev and acceptance commands |
| `docs` | Architecture, API contract and verification evidence |

## Configuration and privacy

`.env.example` documents local settings and reserved provider variables. LLM,
embedding, search and SMTP settings are intentionally unused until their phases.
No user documents are processed or sent externally in Phase 0. No ingestion or
presentation workers run yet. Private specifications, `.env` files, secrets,
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

0. Skeleton and local infrastructure — this release.
1. Streaming chat and persisted sessions.
2. PDF ingestion and grounded retrieval.
3. Meeting intelligence, tasks, and approved email.
4. Durable, time-aware memory.
5. Live search and PowerPoint generation.
6. Hardening and complete demonstration.

Development stops at each phase gate for owner approval. See [AGENTS.md](AGENTS.md)
for contributor commands and migration discipline. No push or later phase is
authorized by this delivery.
