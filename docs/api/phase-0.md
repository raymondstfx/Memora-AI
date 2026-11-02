# Phase 0 API contract

Only `GET /api/health` is implemented. Feature APIs begin in later phases. FastAPI
publishes `/openapi.json` and `/docs`; checked-in `docs/api/openapi.json` drives
`frontend/src/types/api.generated.ts`. No credentials or private specification
content may appear in these artifacts.

## GET /api/health

Public local readiness endpoint; it exposes dependency states, not connection
strings. Every response has an `X-Request-ID` header generated server-side.

200 response:

```json
{"status":"ok","service":"memora-api","version":"0.1.0","dependencies":{"postgres":"ready","pgvector":"ready","schema":"ready","redis":"ready"}}
```

503 response:

```json
{"code":"DEPENDENCIES_UNAVAILABLE","message":"One or more dependencies are not ready.","request_id":"uuid","details":{"dependencies":{"postgres":"unavailable","pgvector":"unavailable","schema":"unavailable","redis":"ready"}}}
```

Unhandled server errors use `INTERNAL_ERROR`; route misses use `HTTP_ERROR` and
validation failures use `VALIDATION_ERROR`. Error details never include database
URLs, passwords, exception strings or submitted document text. Dependency probes
use bounded connection/query timeouts and execute concurrently. There are no
Phase 0 retries beyond user-triggered health refreshes.
