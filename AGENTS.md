# Memora AI contributor instructions

## Scope and architecture

The private implementation specification is authoritative. Phase 2 is the current
delivery boundary. Stop at each phase gate; do not implement Phase 3 or push without
the owner's approval. Never add the private MD/PDF specification to Git.

Use a modular FastAPI monolith, React/TypeScript/Vite client, PostgreSQL/pgvector,
and Redis. Later phases add RQ workers and provider adapters behind application
service interfaces. Do not implement fake feature endpoints or simulated AI output.

## Conventions and contracts

- Python 3.13+, Pydantic v2, SQLAlchemy 2; Ruff formatting/lint and mypy.
- TypeScript strict mode; accessible semantic HTML and Tailwind CSS.
- All API endpoints start with `/api`. Errors contain `code`, `message`,
  `request_id`, and optional `details`; return the request ID in a response header.
- Update OpenAPI-derived frontend types with `npm run api:types` in `frontend`
  after exporting the backend schema; check with `npm run api:check`.
- Secrets stay server-side. Root `.env` is shared by Compose and local backend.
  Never log credentials or document contents.
- User-owned rows in later migrations require UUIDs, UTC times and ownership
  checks. Preserve evidence and historical facts. Email requires explicit approval.
- Phase 1 adds demo users, conversations, messages and durable LangGraph checkpoints.

## Commands (from repository root unless stated)

```text
docker compose --profile app up --build -d --wait
docker compose up -d --wait postgres redis
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-dev.lock
python scripts/dev.py migrate
python scripts/dev.py api
python scripts/dev.py check
python scripts/test_phase1.py
python scripts/test_phase2.py
```

On Unix, use `.venv/bin/python` instead of `.venv/Scripts/python`. Activate the
environment before running `scripts/dev.py`. In `frontend`, use `npm ci`,
`npm run dev`, `npm run check`, and `npm run build`. In Windows PowerShell use
`npm.cmd` if execution policy blocks `npm.ps1`.

## Migrations and verification

Never use `metadata.create_all()` as an alternative to Alembic. Each schema change
needs a reviewed migration and a real Postgres upgrade/downgrade/upgrade test.
Run destructive downgrade tests only against the isolated test Compose project.
Run relevant real tests, formatting, lint, typecheck and frontend build before
reporting completion. Record exact commands, outcomes and blocked checks in
`docs/evals/phase-2.md`. A skipped/blocked integration test is not a pass.

Runtime chat must never use a fake-provider fallback. Test fixtures live under
`backend/tests` and are excluded from production images. Missing Key/model is an
actionable 503, separate from infrastructure health. Do not execute live model
verification without explicit opt-in; credentials are supplied locally by the owner.

Phase 2 adds PDF documents/chunks/jobs, private storage and RQ workers. Never mark
partial ingestion ready. Embedding provider/model/dimensions/Base URL identify an
index; incompatible profiles require explicit reindexing. Never mix vectors or
silently fall back to mock embeddings. PDF evidence cannot execute instructions.
