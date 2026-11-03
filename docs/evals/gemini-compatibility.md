# Gemini compatibility follow-up (Phase 2 only)

Date: November 3, 2026 (Asia/Shanghai). No Phase 3 features added.

Subsequent resolution: [model discovery and bounded live verification](gemini-model-resolution.md)
selected `gemini-3.1-flash-lite` with `minimal` thinking and passed streaming plus
a page-verified RAG answer. Configuration tables below preserve the earlier 404
investigation; use the resolution report for current model/thinking settings.

## Result and exact live request accounting

The owner supplied backend-only local credentials and explicitly authorized
minimal real verification. **Four real HTTP requests total**, no automatic
retries, no model fallback, no model-list discovery request and no extra live run:

| Request | Endpoint/model | Actual result |
| --- | --- | --- |
| 1 | `embeddings`, `gemini-embedding-001`, one PDF chunk, `dimensions:768` | HTTP 200, actual length 768; old strict index-field parser rejected the response; no ready index published |
| 2 | Same model, one tiny PDF chunk, after explicit adapter fix | HTTP 200, length 768; Gemini omitted `index`; normalized and committed, ingestion ready |
| 3 | Same model, one question | HTTP 200, length 768; real Postgres cosine/full-text retrieval returned PDF evidence; repeating the question made zero extra HTTP calls |
| 4 | `chat/completions`, `gemini-2.5-flash-lite` | HTTP 404; `reasoning_effort:"none"`, `max_tokens:1024`, `stream:true` actually sent; no accepted answer |

The initial preflight with empty keys sent **zero** requests. After the first
real response exposed the missing-index compatibility issue, the adapter was
fixed and the verifier was explicitly resumed with the remaining three-request
budget. This was a controlled developer verification, not an automatic job retry.
No live 429 was deliberately induced. Actual quota causes/retry timing are tested
with isolated HTTP fixtures, not claimed to have occurred live.

The single-page synthetic PDF contains only a project deadline and demo owner.
Actual stored vector length was **768**, L2 norm **1.0**. Installed pgvector was
**0.8.7**; actual chunk indexes were B-tree and GIN, with no ANN index. Temporary
document/original/chunks/jobs/cache were removed after verification. A synthetic
fixture and sanitized machine-readable result remain in ignored
`data/gemini-verification/tiny-brief.pdf` and
`logs/gemini-live-verification.json`. No credentials, document text or vectors are
logged in the report. Query cache keys are owner/profile/text-hash scoped; query
vectors normally expire by TTL and the verifier clears its query cache.

**Phase 1 real LLM acceptance remains pending. Phase 2 full real RAG acceptance
remains pending.** The Embedding/SQL retrieval smoke passed, but HTTP 404 prevented
grounded generation, citations from a real model, live SSE/history/restart gates
and semantic answer-quality review. Batch requests containing multiple strings
are covered by fixture tests; this minimal live PDF required only one string per
Embedding request, so real multi-string batching is not claimed as verified.

The HTTP 404 establishes that this model/endpoint was unavailable to this project
at verification time; it does not prove all Gemini 2.5 models are shut down.
Google's current lifecycle documentation describes prior-use restrictions for
2.5 access. Project permissions/model access are a possible cause, not confirmed
by a separate diagnostic request. Configure an accessible model explicitly in
`.env` line 19 before future verification. Do not assume `reasoning_effort=none`
is supported by a different model family. No replacement was silently selected.

## Backend configuration and request mapping

Root `.env` is ignored by Git; `.env.example` contains empty Key placeholders.
Existing owner keys are preserved. Both files retain matching line positions:

| Variable | Line | Value/effect |
| --- | --- | --- |
| `LLM_MODEL` | 19 | `gemini-2.5-flash-lite` requested; current project returns 404 |
| `LLM_API_KEY` | 21 | Owner fills locally; `Authorization: Bearer` only |
| `LLM_BASE_URL` | 23 | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `LLM_TOKEN_PARAMETER` | 25 | Sends `max_tokens` instead of `max_completion_tokens` |
| `LLM_MAX_CONCURRENT_REQUESTS` | 35 | 1, per supported single API process; no wire field |
| `EMBEDDING_API_KEY` | 38 | Owner fills locally; may use the same Gemini Key |
| `EMBEDDING_BASE_URL` | 40 | Same official API root; adapter appends `/embeddings` |
| `EMBEDDING_MODEL` | 43 | `gemini-embedding-001`, sent as `model` |
| `EMBEDDING_DIMENSIONS` | 44 | 768, sent as `dimensions`, actual reply validated |
| `EMBEDDING_SEND_DIMENSIONS` | 47 | true; do not turn off for this 768-dimensional profile |
| `EMBEDDING_BATCH_SIZE` | 50 | 8; ingestion groups strings into `input` arrays |
| `LLM_REASONING_EFFORT` | 73 | `none`, top-level Chat Completions request field |
| `PROVIDER_RETRY_MAX_WAIT_SECONDS` | 75 | 15; local upper bound, never overrides a longer server hint |
| `EMBEDDING_NORMALIZE` | 77 | true; local L2 normalization after length/finite/norm validation |
| `EMBEDDING_MAX_INPUT_BYTES` | 80 | 1800; local query guard and page-preserving chunk byte bound |
| `EMBEDDING_MAX_CONCURRENT_REQUESTS` | 82 | 1, shared Redis slots across API/worker |
| `EMBEDDING_MIN_INTERVAL_SECONDS` | 84 | 4, Redis pacing for uncached batches |
| `EMBEDDING_CACHE_TTL_SECONDS` | 86 | 86400; local private vector-cache expiry |

All new environment variables are included in the Compose shared backend
environment used by API and worker. Local backend reads the same root `.env`.
Transport tests inspect actual JSON/headers. Local controls are applied by the
application rather than sent as unsupported Gemini request fields. Normal runtime
still refuses missing keys/model and never falls back to simulated providers.

The embedding request is `{model,input:[...],encoding_format:"float",dimensions:768}`.
No Gemini native `output_dimensionality`, `task_type`, `title`, or thinking fields
are invented for this compatibility endpoint. Gemini may omit/null all result
indices; only the official Gemini hostname permits input-order mapping after
exact count validation. Mixed/missing generic-provider indices, wrong dimensions,
nonfinite/zero vectors and partial batches remain errors.

Gemini's default embedding size is 3072; 768 is an officially recommended reduced
size. `gemini-embedding-001` requires normalization when reduced. No response is
silently truncated. The model's 2048-token input limit motivates the conservative
UTF-8 byte guard; it is not an exact provider tokenizer/countTokens verification.
Long cached chunks fail clearly and require explicit `--reparse`, rather than
provider-side silent truncation or automatic repeat indexing.

## Index identity, caching and quota behavior

Existing schema uses variable-dimension `vector` and exact cosine search plus GIN
full-text ranking. Vector storage supports up to 16000 dimensions; ordinary
HNSW/IVFFlat vector indexes up to 2000. 768 fits both; no schema migration or new
ANN index was introduced. Provider/Base URL/model/dimensions/normalization identify
the index. Key changes do not change the profile. Changing the profile requires
explicit rebuild; old vectors are never reused in an incompatible profile.

```powershell
# From root, after local environment/dependencies are ready:
.venv\Scripts\python scripts/reindex_documents.py --document <uuid>
# If existing chunks exceed the new byte limit:
.venv\Scripts\python scripts/reindex_documents.py --document <uuid> --reparse
```

Do not use `--all` just to test credentials. Ready documents are reused on upload;
failed jobs stay failed until explicitly retried. Successful batch vectors survive
a later batch failure in Redis and can be reused during retry. Document cache
keys include owner/document/profile/content hash; query cache uses owner/profile/
question hash. Raw text and credentials are not stored in cache keys/values.
Deletion purges that document's vector cache; Redis eviction/TTL expiry can cause
a later explicit operation to regenerate vectors. Cache is an optimization, not a
permanent index replacement. Redis admission failure stops before upstream calls.

Chat is serialized within the supported one-process API. Embedding concurrency is
enforced across API and workers, with bounded pacing and no unbounded local queue.
Default active ingestion cap is one. Batch size 8 reduces HTTP overhead; it does
not eliminate project/model RPM, TPM or RPD limits, guarantee a free allowance,
or make a large PDF a suitable first test. Check actual AI Studio project quotas.

429 errors are classified as daily quota, unavailable/zero quota/billing, token
rate, request rate or unknown. Daily/unavailable quota never auto-retries. Retry
timing honors the larger valid `Retry-After` (seconds/HTTP date) / Google
`RetryInfo.retryDelay` hint, with at most configured retries (default one). Hints
over 15 seconds stop instead of retrying early. Known minute limits without a
hint use bounded backoff; unknown 429 without a hint stops. 502/503/504 retries
remain bounded. Partial chat output is never replayed. Error bodies are sanitized.
No automatic RQ requeue, automatic index rebuild or provider/model fallback exists.

## Verification commands and evidence

Publication note: at the owner's request, new verification/test sources and local
changes to previously tracked test runners are excluded from this publication.
The commands and results below record the verified local workspace; the new
Gemini verifier and test cases are not included in a fresh public checkout.
Previously published tests remain in Git history; this update does not remove
them or claim that ignored files already tracked by Git become untracked.

Final checks actually executed:

| Check | Result |
| --- | --- |
| `.venv\Scripts\python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy on 38 application files, **50 unit tests** |
| `python scripts/test_phase2.py` with test port override below | PASS: **22 real integration tests + 12 Playwright tests**, independent fixture providers |
| Same isolated runner | PASS: Linux images, RQ ingestion, schema upgrade/downgrade/upgrade, drift checks, dependency recovery and restart persistence |
| `npm.cmd run check` / `npm.cmd run build` in `frontend` | PASS: formatting, strict types, OpenAPI type freshness, Vite production build |
| Compose configuration mapping | PASS: all seven newly introduced environment variables match effective Settings for both API and worker |
| `docker compose --profile app up --build -d --wait` | PASS: normal API/frontend/Postgres/Redis/worker healthy; migration exits 0 |
| Running-container Settings check | PASS: API and worker both load `reasoning_effort=none`, dimensions 768, batch 8, normalization true |
| Local `/api/health` and config endpoints | PASS: health 200, chat/Embedding configured true; configured means settings present, **not** model availability |
| Private-file / configured-secret scan and `git diff --check` | PASS: local Key files, private specs and runtime evidence remain excluded |

Final isolated command (from root):

```powershell
$env:BUILDKIT_NO_CLIENT_TOKEN = '1'
$env:PLAYWRIGHT_CHANNEL = 'msedge'
$env:MEMORA_TEST_FRONTEND_PORT = '55273'
.venv\Scripts\python scripts/test_phase2.py
```

The host initially had Docker stopped with a stale communication-socket startup
error; restarting Docker Desktop recovered the engine without deleting/resetting
volumes. Windows reserved port range 55088–55187 then blocked default test port
55173. The test runner now accepts `MEMORA_TEST_FRONTEND_PORT`; 55273 was used.
An intermediate browser run exposed a test waiting on the old `ready` state
before a new rebuild finished. The test now waits on the returned job ID reaching
`succeeded`; no production limit was relaxed. Final output was `22 passed`,
`12 passed` and all three acceptance PASS markers. The isolated project, volumes
and fixture HTTP process were cleaned by the runner. Full output is retained in
ignored `logs/gemini-regression.log`; normal-stack startup output is in
`logs/gemini-stack-startup.log`.

The owner-approved live commands were run from `backend` so parser subprocesses
resolve the application module:

```powershell
..\.venv\Scripts\python ../scripts/verify_live_gemini.py --run-live
# Explicitly after fixing the observed response parser, within same total budget:
..\.venv\Scripts\python ../scripts/verify_live_gemini.py --run-live --resume-after-fix
```

The verifier makes no model-list request. Its four-request budget includes
failures, retries are disabled, and a resumed run accounts for previous requests.
Do not rerun it now: the budget was consumed and model access must be resolved.
It runs the production ingestion/retrieval/provider service code locally with
real PostgreSQL/Redis, bypassing enqueue only to control external-call accounting.
This live check does not claim browser-to-RQ-to-model end-to-end acceptance.
The separate fixture regression exercises the real RQ/container/browser path.

Start/recreate API and worker after editing configuration:

```powershell
docker compose --profile app up --build -d --wait
```

## Primary references checked

- [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai):
  API root, thinking disable field, streaming and Embedding endpoint.
- [Gemini embeddings](https://ai.google.dev/gemini-api/docs/embeddings):
  dimensionality, normalization and model input limits.
- [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits):
  project-scoped RPM/TPM/RPD; actual limits depend on project/model.
- [Gemini lifecycle](https://ai.google.dev/gemini-api/docs/deprecations) and
  [Firebase troubleshooting](https://firebase.google.com/docs/ai-logic/faq-and-troubleshooting):
  model access restrictions; HTTP 404 still requires project-specific review.
- [pgvector](https://github.com/pgvector/pgvector): exact search, vector storage
  and ANN dimensionality limits.
