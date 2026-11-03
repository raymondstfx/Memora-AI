# Phase 2 delivery and verification

Date: November 3, 2026 (Asia/Shanghai).

Gemini follow-up: see [the measured compatibility report](gemini-compatibility.md).
Four real requests were subsequently authorized and sent. Real 768-dimensional
Embedding ingestion/storage and hybrid retrieval passed on a tiny PDF; the
requested chat model returned HTTP 404. Full Phase 1 real-model and Phase 2 RAG
acceptance remain pending. The keyless baseline below is the original handoff
record, not a claim that the later live smoke test was never attempted.

## Scope and acceptance status

Phase 2 implementation and credential-independent acceptance are complete.
**Phase 1 real LLM acceptance: pending verification. Phase 2 real Embedding/RAG
acceptance: pending verification.** No real provider keys were supplied, no real
external LLM/Embedding calls were made, and test results are not claimed as live
provider acceptance. Phase 3 has not started. The owner subsequently authorized
publishing the completed Phase 1/2 work as separate, meaningful Git commits.

The specification, AGENTS.md, existing implementation and Phase 1 report were read
before changes. The existing modular FastAPI/React/Postgres/Redis architecture,
chat API, ownership checks, error envelope and OpenAPI-derived types are retained.

## Delivered changes

- Alembic `0003_pdf` adds scoped documents, chunks, processing jobs and persisted
  chat PDF IDs. Chunks retain page, ordinal, text hash, approximate token count,
  embedding profile/dimension metadata and a GIN-indexed full-text vector.
- PDF upload checks extension, MIME, signature and size, with bounded multipart
  ingress before framework spooling. UUID storage paths remain outside the web
  root. SHA-256 duplicate uploads reuse their document/job.
- Real Redis/RQ workers use JSON-serialized UUID jobs and private persistent file
  volumes. Native PyMuPDF extraction runs in a bounded subprocess. Page/text/chunk
  limits, Linux parser memory limits and job timeouts are enforced.
- Page-preserving overlapping chunks are cached independently of embeddings.
  Unsupported/corrupt/encrypted/textless or partially textless files fail clearly.
  Missing Embedding settings do not produce ready indexes. Retry reuses parsed
  chunks; an explicit reparse path is provided.
- Embedding adapter validates configuration, response indices/count, actual
  dimension, finite values and nonzero norm. Application services revalidate the
  provider boundary. Retry/backoff is bounded and errors are sanitized.
- Hybrid retrieval filters ownership, readiness and compatible index profiles,
  combines pgvector cosine and Postgres full-text rankings through RRF, and uses
  deterministic tie ordering. The small demo uses exact vector search, not ANN.
- Chat accepts ready owned PDFs, emits actual retrieval activity and validated
  source events. Structured answer/citation validation permits only retrieved
  keys, with one repair attempt. Invalid citations never become accepted answers.
  PDF answers are buffered until validation; ordinary chat keeps token streaming.
- Knowledge Base exposes upload, stages/progress, errors, retry/reparse, explicit
  reindex, original download and deletion. Chat shows PDF selectors and persisted
  filename/page/excerpt cards linked to the owned original.
- Model/profile changes are explicit: provider/Base URL/model/dimensions form a
  fingerprint. Incompatible indexes become `needs_reindex`; old vectors cannot
  silently participate. Rebuilds can use the UI or `scripts/reindex_documents.py`.
- Compose adds a health-checked worker and private volume. A hybrid override shares
  host-private files with the container worker for local API/Vite development.
  README, `.env.example`, contributor instructions, API docs and lockfiles are updated.

## Commands and actual final results

Windows commands used `.venv\Scripts\python` and `npm.cmd`.

| Executed check | Result |
| --- | --- |
| `python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy on 36 application source files, **35 unit/contract tests**; 20 integration cases deselected intentionally |
| PDF/failure/lease integration group on isolated Postgres | PASS: **12 tests** using native parser subprocesses and actual pgvector/full-text queries |
| `python scripts/test_phase2.py` | PASS: **20 integration tests + 12 Playwright tests**, actual RQ worker and Linux builds |
| `npm run check` | PASS: formatting, strict TypeScript and generated API contract freshness |
| `npm run build` | PASS: Vite production build; frontend also builds inside Linux image |
| `python scripts/export_openapi.py` / `npm run api:types` | PASS: application schema and generated client types synchronized |
| `python -m pip check` | PASS: no broken requirements |
| `docker compose --profile app up --build -d --wait` | PASS: API/frontend/Postgres/Redis/worker healthy; migration exits 0 |
| Hybrid Compose configuration validation | PASS: `docker compose -f docker-compose.yml -f docker-compose.hybrid.yml --profile app config --quiet` |
| Normal-stack keyless ingestion | PASS: actual upload/RQ parse saves 2 chunks, then fails with `EMBEDDING_NOT_CONFIGURED`; never ready; verification document subsequently deleted |
| Normal-stack provider readiness | PASS: `/api/chat/config` and `/api/documents/config` both report `configured:false`; health is 200 |
| Index rebuild CLI | PASS: argument/help validation; rebuild behavior exercised through real service and browser/API tests |
| `git diff --check` / `git check-ignore` | PASS: `.env`, private MD/PDF and runtime fixture files excluded |

Final isolated run:

```powershell
$env:BUILDKIT_NO_CLIENT_TOKEN = '1'
$env:PLAYWRIGHT_CHANNEL = 'msedge'
.venv\Scripts\python scripts/test_phase2.py
```

Final output includes `20 passed`, `12 passed`, and
`PASS: Phase 2 PDF/RQ/hybrid/citation acceptance (test providers only)`.
Raw output is retained locally in ignored `logs/phase-2-acceptance.log` and
`logs/phase-2-startup.log`. Browser evidence is in ignored `frontend/test-results/`;
the source-card screenshot was inspected.

## What the tests establish

| Area | Evidence |
| --- | --- |
| Upload boundaries | Wrong extension/MIME/header and oversized body/file rejected; no document rows created |
| A03 PDF ingestion | Real RQ worker parses/indexes a two-page fixture; page and chunk counts positive, state ready only after all vectors commit |
| A04 grounding/citations | Fixture answer references the API deadline with original filename/page; source route returns actual PDF; reload preserves citations |
| A05 unsupported PDF | Corrupt, encrypted, scanned/empty and partially textless inputs fail, without ready success |
| Duplicate safety | Repeated same-owner upload returns the same document/job; repeated worker execution does not duplicate chunks or attempts |
| Independent retry | Missing Key retains extracted chunks; later injected valid provider retries embedding without reparsing |
| Index rebuild | Model and dimensions change; old index rejected; explicit rebuild creates compatible vectors; retrieval works afterward |
| Queue/provider failure | Redis enqueue outage and malformed vector shape become explicit failed records; no partial ready index |
| Worker state | A failed/expired job cannot resume publishing chunks/vectors or resurrect ready status |
| Hybrid SQL retrieval | Actual cosine and GIN/full-text ranks are fused; deterministic test vectors do not claim real semantic quality |
| A19 restart persistence | Original PDF bytes, ready metadata and hybrid retrieval survive API/Postgres/worker restart; chat and Redis/Postgres probes also persist |
| A20 scope | Other identity cannot access document metadata/file/job or select its evidence; scope filtering occurs before retrieval |
| Prompt/citation boundary | No executable later-phase tools; unknown source IDs fail after bounded repair; no invented citation cards accepted |
| Lifecycle | Migration upgrade/downgrade/reapply and schema drift check; deleting document removes original, chunks/vectors and jobs |

The 12 browser tests include existing chat/regression checks plus PDF upload,
async ready state, duplicate upload, rebuild, grounded source card/reload/original,
corrupt-file retry and missing-Embedding guidance. The independent test HTTP
provider supplies deterministic embeddings and structured fixture answers. Test
providers are not copied into production images; no runtime fake-provider setting
or automatic fake-success fallback exists.

The full runner uses the isolated `memora-phase2-test` project, disposable volumes
and a temporary upstream process. These are cleaned up after the run. A separate
temporary local Postgres database used for focused checks is also removed after
verification. Normal development volumes remain. Generated synthetic PDFs under
ignored `data/phase2-fixtures/` can be reused for manual validation.

Resolved verification issues included a tied hybrid rank needing a lexical
tie-break, expanded fixture imports, deprecated RQ callback invocation and a host
proxy intercepting loopback HTTPX requests. Test-local loopback clients now bypass
environment proxies; production external-provider proxy behavior was not changed.
Final checks above were actually executed after fixes, not inferred from builds.

## Exact configuration locations

Edit **root `.env` only** for actual credentials. The current `.env.example` has
the same line positions with comments and deliberate placeholders:

| Setting | `.env` line | Purpose |
| --- | --- | --- |
| `LLM_MODEL` | 19 | Exact supported chat model ID |
| `LLM_API_KEY` | 21 | Real LLM Key |
| `LLM_BASE_URL` | 23 | Chat API root |
| `EMBEDDING_API_KEY` | 38 | Separate real Embedding Key |
| `EMBEDDING_BASE_URL` | 40 | Embedding API root, not `/embeddings` |
| `EMBEDDING_MODEL` | 43 | Exact supported Embedding model ID |
| `EMBEDDING_DIMENSIONS` | 44 | Matching actual vector dimension; 0 deliberately disables success |
| `EMBEDDING_SEND_DIMENSIONS` | 47 | False for providers without this request parameter; returned dimension still validated |

Both APIs support configured OpenAI-compatible endpoints. No Key/model is
hardcoded in application source. Real `.env` is ignored; never place credentials
in `.env.example`, frontend source or `VITE_*` variables.

After configuration, recreate API and worker:

```powershell
docker compose --profile app up --build -d --wait
```

After changing provider/Base URL/model/dimensions, explicitly rebuild:

```powershell
.venv\Scripts\python scripts/reindex_documents.py --all
# Or: --document <uuid>; add --reparse to recreate chunks from the original.
```

Poll Knowledge Base/jobs until ready. Queue submission is not success. Missing or
invalid configuration still fails honestly and preserves retryable parsed data.

## Remaining unverified gates and practical limits

- **Phase 1 real LLM acceptance remains pending.** No live-key model call, account
  permission, actual response latency/quality or billing was verified.
- **Phase 2 real Embedding/RAG acceptance remains pending.** Real model/dimension
  support, provider semantics, embedding quality and factual grounded answer
  quality have not been verified. Structural citation validation is not a proof
  that a model's claim is semantically entailed by its source.
- Containerized RQ is the verified execution path. Hybrid configuration validates;
  native Windows worker and the bind-mounted hybrid path were not independently
  exercised end to end. Native Windows PDF parsing was exercised in tests.
- No OCR. A textless page fails the entire PDF for explicit review; valid blank
  pages should be removed before ingestion. Chunk tokens are approximate units;
  provider tokenizer/context behavior needs live validation.
- Exact vector search is suitable for this bounded demo. Large-corpus ANN tuning,
  complex PDF layout extraction and multilingual semantic quality are not claimed.
- Fixed demo identity and loopback deployment remain; no public auth or Phase 3
  meeting/task/email functionality is introduced.

To finish live acceptance later: configure both providers, upload the synthetic
brief or a known PDF, wait for ready, ask its API deadline, inspect filename/page
against the original, reload/restart and repeat; test wrong dimensions/Key, then
explicitly rebuild after a model change. For Phase 1, use the documented opt-in
`scripts/verify_live_chat.py --run-live`. No live verification command was run now.
Stop at Phase 2 until the owner explicitly requests Phase 3.
