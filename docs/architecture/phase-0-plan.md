# Phase 0 implementation plan

Status: written before application code. Scope: skeleton and local infrastructure.

1. Exclude private specification, secrets, generated dependencies and runtime data.
2. Establish this plan and contributor conventions; set the requested Git origin.
3. Configure Compose with pgvector/Postgres and Redis, named persistent volumes,
   health checks, loopback-only published ports and optional app profile.
4. Add shared environment configuration, FastAPI startup, structured request logs,
   machine-readable errors, dependency readiness and an Alembic baseline.
5. Build a responsive React/Vite/Tailwind navigation shell, honest placeholder
   pages and an actual API health panel with loading/error/retry states.
6. Export OpenAPI and generate TypeScript contracts. Add reproducible checks.
7. Execute real unit/contract tests, Postgres/Redis integration, migration reversal,
   frontend formatting/typecheck/build and full-stack HTTP smoke checks.
8. Record results and stop. No push or Phase 1 work.

## Module architecture

`frontend/src/app` owns navigation. `components` contains reusable UI elements,
`features` the infrastructure health view, `lib` API access, `types` generated
OpenAPI types. API routes live in `backend/app/api`; settings, logging and errors
in `core`; SQLAlchemy engine and base metadata in `db`; public schemas in
`schemas`. Later phases introduce agents, workers and provider services without
changing the modular monolith boundary.

Compose starts healthy dependencies, runs migrations once, then starts the API
and UI. Hybrid mode starts only dependencies and uses host loopback URLs from
`.env`. Containers override dependency URLs with Compose DNS names. No external
LLM, search or email credentials are needed for Phase 0.

## Database design

Baseline `0001_infrastructure` enables the `vector` extension and creates
`system_metadata` with key, value and UTC created/updated timestamps. A schema
version row demonstrates migration ownership. It has no user data. Users,
conversations and messages start in Phase 1; remaining feature tables follow
their delivery phases. Alembic is the only schema management mechanism.

Downgrade removes the baseline table but retains the shared vector extension to
avoid deleting unrelated vector objects. An isolated integration test verifies
upgrade -> downgrade base -> upgrade head.

## Test plan and exact gate

- One documented command starts dependencies: `docker compose up -d --wait postgres redis`.
- One documented command starts the full stack:
  `docker compose --profile app up --build -d --wait`.
- `GET /api/health` returns 200 only when Postgres is reachable, vector is enabled,
  the schema revision is current, and Redis responds; otherwise 503 with standard
  error fields and per-dependency readiness details.
- Migration applies, reverses, and reapplies on real pgvector/Postgres.
- Unit tests validate configuration/error contracts; integration tests exercise
  actual dependency readiness, failure/recovery and persistence after restart.
- OpenAPI export and generated TypeScript types agree.
- Ruff, mypy, frontend formatting/typecheck and production build pass.
- The UI exposes seven navigation destinations without claiming future features
  work. Health calls the real backend and supports retry.
- Private specifications and runtime/secrets remain ignored; origin is correct.

References: [Compose startup ordering](https://docs.docker.com/compose/how-tos/startup-order/),
[FastAPI containers](https://fastapi.tiangolo.com/deployment/docker/),
[Vite prerequisites](https://vite.dev/guide/).
