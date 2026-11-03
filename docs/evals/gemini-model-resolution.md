# Gemini chat 404 resolution

November 3, 2026 (Asia/Shanghai). Phase 2 boundary retained; no Phase 3 work.

## Selection

One authenticated `GET https://generativelanguage.googleapis.com/v1beta/models`
with `pageSize=1000` returned HTTP 200, no next page. Authentication used the local
backend Key in a header, never a query string or log. Candidates were filtered by
`supportedGenerationMethods` containing `generateContent`; the returned list
included stable `gemini-3.1-flash-lite` as well as Flash/preview/newer variants.
The old `gemini-2.5-flash-lite` also appeared, illustrating that listing alone
does not establish runtime access. It was not tried again.

Selected **gemini-3.1-flash-lite**: stable explicit ID, text generation capability,
official free input/output tier, and low paid rates ($0.25 input / $1.50 output
per million text tokens). Preview IDs and floating `latest` aliases were avoided.
This is a low-cost choice, not a claim that it is the cheapest available model.
Free-tier availability does not prove this account is on a free plan or guarantee
remaining quota; actual billing was not independently audited.

The official OpenAI compatibility table maps `reasoning_effort=minimal` to
Gemini 3.1 Flash-Lite's minimal thinking level. The request now sends `minimal`,
not `none`; this minimizes thinking rather than claiming it is disabled.

Sources checked:

- [Model and stable ID](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)
- [Free and paid pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-lite)
- [Thinking compatibility mapping](https://ai.google.dev/gemini-api/docs/openai#thinking)

## Actual requests and results

Exactly **5 external API requests this follow-up**, no automatic retry, model
fallback, JSON repair or repeated candidate attempts:

| Order | Request | Result |
| --- | --- | --- |
| 1 | Official models list | 200, one page; model discovery only |
| 2 | Streamed Chat Completions, `gemini-3.1-flash-lite`, `minimal` | 200; nonempty SSE text, valid stop and `[DONE]`; one text delta for the tiny prompt |
| 3 | `gemini-embedding-001`, one synthetic PDF chunk | 200, actual length 768 |
| 4 | Same Embedding model, one question | 200, length 768; hybrid retrieval yielded evidence; repeat query used cache with zero extra calls |
| 5 | Streamed Chat Completions for the retrieved evidence | 200; JSON/citation validation passed without repair; deadline correct and cited page 1 matched native extraction from the original PDF |

There were no document rows available to reuse. The verifier first indexed one
single-page synthetic PDF through the existing ingestion service; it did not
call reindex/reparse, change Embedding settings or rebuild an existing index.
The existing Key, model, Base URL, dimensions, normalization and index profile
were retained. The sample original/document/chunks/jobs were removed afterward;
the matching query cache remains available until its normal TTL. No broad cache
flush occurred. No real documents or their contents were logged.

Sanitized evidence is local and Git-ignored:
`logs/gemini-model-discovery.json` and `logs/gemini-model-fix.json`.
Only model/request metadata and validation outcomes are recorded, not keys,
prompts, PDF contents, generated answers or vector values. No further live
requests were made after success.

## Exact configuration

Root `.env` and `.env.example` retain matching positions:

| Setting | Line | Current value |
| --- | --- | --- |
| `LLM_MODEL` | 19 | `gemini-3.1-flash-lite` |
| `LLM_API_KEY` | 21 | Owner-supplied locally; example blank |
| `LLM_BASE_URL` | 23 | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `LLM_TOKEN_PARAMETER` | 25 | `max_tokens` |
| `LLM_REASONING_EFFORT` | 73 | `minimal`; comment explains `none` is unsupported |
| `EMBEDDING_API_KEY` | 38 | Unchanged owner-supplied local value |
| `EMBEDDING_BASE_URL` | 40 | Unchanged official compatibility API root |
| `EMBEDDING_MODEL` | 43 | Unchanged `gemini-embedding-001` |
| `EMBEDDING_DIMENSIONS` | 44 | Unchanged 768 |

The existing adapter already transmits this reasoning setting; no new provider
code, database migration or API schema was needed. API and worker were recreated
with `docker compose --profile app up -d --wait api worker`. Startup/config checks
do not send model requests. `.env` remains ignored; test/runtime artifacts remain
excluded according to the owner's publication preference.

This is a narrow real-provider service/transport smoke: streaming chat followed
by native PDF ingestion, real Embedding, Postgres hybrid retrieval and a validated
answer/page citation. It does not claim browser-to-worker live acceptance,
conversation reload/restart/cancellation verification, broad semantic quality or
account billing audit. Complete Phase 1/2 live gates remain pending those checks.
The full real-API test suite was deliberately not run.

Final local checks: `python scripts/dev.py check` passed Ruff lint/format, strict
mypy (38 application files), and 50 unit/contract tests with 22 integration tests
intentionally deselected. No frontend/application source changed, so no new
frontend build or full fixture integration run was needed for this configuration
change. Normal Compose API/worker startup passed; local health returned 200 and
the loaded API model/thinking values were checked without provider calls.
