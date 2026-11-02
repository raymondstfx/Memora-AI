# Phase 0 delivery and verification

Date: November 2, 2026 (Asia/Shanghai).

## Delivered scope

Phase 0 implements local infrastructure and the application skeleton only.
There are no feature APIs, model calls, document uploads, email sends, agents or
presentation jobs. The navigation shell explicitly labels each future feature
with its delivery phase. Phase 1 has not started.

- Initialized Git on `main`; origin is
  `https://github.com/raymondstfx/Memora-AI.git`. Nothing was pushed.
- Created `.gitignore` before application code and excluded both private
  specification formats, `.env`, secrets, dependencies, caches and runtime data.
  `.dockerignore` excludes private inputs from image build contexts as well.
- Added Compose with Postgres/pgvector, Redis, named persistent volumes,
  health checks, migration-before-API startup, non-root application containers,
  loopback-only ports and an optional `app` profile.
- Implemented shared environment configuration, SQLAlchemy metadata/session
  factory, reversible Alembic baseline, real dependency health, machine-readable
  errors, request IDs and sanitized structured API logs.
- Built React/TypeScript/Vite/Tailwind navigation for all seven destinations,
  an owned shadcn-style button primitive and real readiness with loading,
  unavailable and retry states. No simulated feature functionality is exposed.
- Added OpenAPI export, generated client types and drift checks against both the
  running application schema and frontend types.
- Added public README, contributor instructions, architecture/API documents,
  locked dependencies and cross-platform dev/test commands.

## Acceptance gate

| Gate | Result | Executed evidence |
| --- | --- | --- |
| One command starts dependencies | PASS | `docker compose up -d --wait postgres redis`; both healthy |
| One command starts complete stack | PASS | `docker compose --profile app up --build -d --wait` on the development stack and isolated acceptance project; API and frontend healthy, migration exited 0 |
| API health succeeds | PASS | Direct API and Nginx-proxied `GET /api/health` return 200 with all four readiness states |
| Migration applies and reverses | PASS | Real Postgres upgrade → downgrade base → upgrade head; table removal and health 503 verified; Alembic drift check passes |
| pgvector is operational | PASS | Real vector distance SQL returns zero for identical vectors |
| Frontend builds | PASS | Strict TypeScript and Vite production build on Windows and inside Linux image |
| Dependency failure is honest | PASS | Stop real Redis → health 503; restart → health 200 |
| Data persists after restart | PASS | Insert Postgres row and Redis key, restart both containers, read original values |
| Browser → API → dependencies → UI | PASS | Playwright against production Nginx stack and separately against hybrid Vite stack |
| Private inputs excluded | PASS | `git check-ignore` confirms MD, PDF, `.env`, dependency and runtime paths; publishable file inventory reviewed |

## Commands actually executed

PowerShell uses `npm.cmd` and `.venv\Scripts\python`; the commands below show
those executable choices. All commands were run locally; this is not a CI claim.

| Command | Final outcome |
| --- | --- |
| `.venv\Scripts\python scripts/dev.py check` | PASS: Ruff lint/format; mypy, 13 source files; 11 unit/contract tests, 1 integration test deselected |
| `.venv\Scripts\python scripts/export_openapi.py` | PASS: checked-in OpenAPI generated |
| `npm.cmd ci` | PASS: executed inside frontend Linux image from lockfile |
| `npm.cmd run check` | PASS: Prettier, strict TypeScript and generated-type drift check |
| `npm.cmd run build` | PASS: production HTML/CSS/JS generated |
| `npm.cmd audit` | PASS: zero vulnerabilities after development glob dependency override |
| `.venv\Scripts\python -m pip check` | PASS: no broken requirements |
| `docker compose config --quiet` | PASS: Compose configuration validates |
| `docker compose up -d --wait postgres redis` | PASS: actual hybrid dependencies healthy |
| `.venv\Scripts\python scripts/dev.py migrate` | PASS: actual development DB at `0001_infrastructure` |
| `python -m pytest tests/integration -q` with isolated DB/reset environment | PASS: 1 integration test; real pgvector and upgrade/downgrade/reapply; no database substitutes |
| `npm.cmd run test:e2e` with hybrid base URL and installed Edge channel | PASS: 3 browser tests |
| `.venv\Scripts\python scripts/test_infrastructure.py` with daemon-side token fetch and Edge channel | PASS: complete Compose acceptance, real migration test, persistence/failure probes and 3 browser tests; isolated containers/volumes cleaned up |
| `git -c safe.directory=D:/Demo remote -v` | PASS: requested origin for fetch/push; no remote writes performed |
| `git -c safe.directory=D:/Demo check-ignore ...` | PASS: private spec, environment, dependencies and runtime data ignored |

The isolated acceptance command uses these terminal environment overrides on this
machine:

```powershell
$env:BUILDKIT_NO_CLIENT_TOKEN = '1'
$env:PLAYWRIGHT_CHANNEL = 'msedge'
.venv\Scripts\python scripts/test_infrastructure.py
```

The runner uses its own project name and ports, and sets the reset flag only for
the isolated database. Integration tests additionally reject database names that
do not end in `_test` or `_isolated`. Raw final acceptance output is retained
locally in ignored `logs/phase-0-infrastructure.log`; browser screenshots and
failure traces belong to ignored `frontend/test-results/`.

## Browser evidence

Three Playwright tests exercise:

1. Live readiness, all sidebar destinations, refresh, proxied API documentation
   and OpenAPI, with no uncaught browser errors.
2. A test-only HTTP 503 interception followed by removal of the interception and
   retry against the actual backend. The production UI contains no mock data.
3. A 390px mobile viewport, navigation switching and no horizontal overflow.

Desktop and mobile screenshots were inspected. The sidebar scrolls on shorter
viewports; future action buttons are disabled and marked with the future phase.

## Validated versions

| Component | Version |
| --- | --- |
| Host Python / Node / npm | 3.13.0 / 22.22.2 / 10.9.7 |
| Docker Engine / Compose | 29.5.3 / 5.1.4 |
| PostgreSQL / pgvector / Redis server | 17.11 / 0.8.7 / 7.4.12 |
| FastAPI / Pydantic / settings | 0.162.0 / 2.14.2 / 2.16.2 |
| SQLAlchemy / Alembic / Psycopg | 2.1.6 / 1.20.1 / 3.3.6 |
| Uvicorn / Redis Python client | 0.54.0 / 7.4.1 |
| pytest / Ruff / mypy | 9.2.0 / 0.17.3 / 1.20.2 |
| React / Vite / TypeScript / Tailwind | 19.3.1 / 8.3.5 / 5.9.3 / 4.3.3 |
| OpenAPI TypeScript / Playwright | 7.13.0 / 1.64.1 |

Full transitive versions are in the lockfiles. Docker references use version
tags; the image content resolved during this run was:

| Image | Resolved SHA-256 digest |
| --- | --- |
| `pgvector/pgvector:pg17` | `7d0a41464797aeb9862dfdc0bbf1526b82cfd324cdd8036df19e3545f4a9ccb8` |
| `redis:7.4-alpine` | `8da19c7399dca900c6822a1cf30f9d2285585e2c4b457ff4095b0f4500054d3f` |
| `python:3.13-slim` | `ae14d4ce8771606477a81446e7ef429edd6762305fc50c84507c1041fa8285d1` |
| `node:22-alpine` | `fe4f6d74e20370acb04ad889077d14d0f64a9c8ea6a42bc60cddf1e844699914` |
| `nginxinc/nginx-unprivileged:1.28-alpine` | `7377697a821c131a924a7105fafbe7414db4e9fcc77a6f08f776f33f141ec3f8` |

## Issues resolved and limits

- Docker was initially stopped; it was started and the engine verified.
- Image pulls initially failed with registry TLS timeouts. A later BuildKit
  client token request failed on host networking. Prefetching base images and
  `BUILDKIT_NO_CLIENT_TOKEN=1` allowed the full build to run successfully. The
  workaround follows [BuildKit guidance](https://github.com/moby/buildkit/issues/4725)
  and leaves TLS and authentication enabled.
- The latest TypeScript major was incompatible with the OpenAPI generator's
  declared peer dependency. TypeScript is locked to compatible 5.9.3 and the
  real contract-generation checks pass.
- The test client was updated to supported HTTPX2. Alembic's path separator is
  explicit; final Python checks have no deprecation warnings.
- Three initial npm advisory entries shared a development-only glob dependency.
  Its patched override is locked and contract generation still passes; final
  audit reports zero vulnerabilities.
- Git's sandbox identity required a per-command `safe.directory` override.
  No global Git configuration was changed.
- The Playwright bundled-browser download stalled and was cancelled. Tests ran
  successfully using installed Microsoft Edge's Chromium engine. The default
  Chromium download remains a documented alternative, not a claimed passed check.
- This is a loopback-only development release without user data or auth. Full
  feature acceptance cases A01–A22 belong to later phases and are not claimed
  complete. Restart persistence here covers infrastructure test records only.

The development stack is left running at `http://localhost:5173`; direct and
proxied health both returned 200 with all dependencies ready after final startup.
Temporary hybrid server processes and the disposable fallback database were
removed. Development volumes were retained.

No Phase 0 acceptance blockers remain. Next authorized work would be Phase 1:
streaming chat and persisted sessions, after explicit owner approval. No push
or Phase 1 implementation was performed.
