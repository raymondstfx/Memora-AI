# Phase 5 delivery and verification

Date: 2026-11-03, Asia/Shanghai. Scope: Phase 5 only; Phase 6 is not started.
Read AGENTS.md, the authoritative private implementation specification and latest
Phase 3/4 reports before implementing. The owner's current request authorizes
this phase despite the earlier phase boundary. No commit or push is performed
for this phase. Earlier local commits and the failed GitHub push remain unchanged.

## Delivered behavior

- Bounded Tavily basic-search adapter returns actual title, URL, snippet,
  optional publication date and UTC retrieval time. Max 5 results, 500-character
  queries, 100 KB response cap and configured timeout; no raw-page fetch, images,
  generated search answer, infinite retry or invented result. HTTP failures and
  missing Key return sanitized actionable errors. One shared Redis search slot
  and per-owner hashed query caches preserve original retrieval timestamps.
- Standalone search UI and explicit `/search query` chat ground responses in
  validated results. Chat persists source URLs/retrieval times and search_web
  metadata with normal stream/checkpoint behavior. Ordinary chat never claims a
  fresh search. Optional web research on a deck is a separate explicit choice.
- Alembic `0006_presentations` adds owned UUID/UTC presentation task state,
  unique per-owner request keys and durable request/outline/source records.
  Public job_id equals presentation id; existing document jobs remain unchanged.
  One active job per owner, bounded RQ execution, stale-job interruption recovery,
  explicit retries up to three attempts and audit records prevent blind replay.
- Context combines selected ready PDFs through the existing hybrid retriever,
  checksum-verified meeting extraction, owned memory retrieval and optional web.
  Existing Gemini model/reasoning/Base URL, Embedding profile, caching and shared
  Redis LLM admission are retained. No vector index is rebuilt. Model output
  cap and configured connect/read/total timeouts are applied to planning.
- Strict slide schema enforces explicit exact count, language, supported variants,
  bounded title/bullets/notes, fixed theme, visual_spec=none and known citations.
  Every sourced slide requires source references. Schema/citation/count errors
  fail explicitly; there is no fake outline fallback or automatic repair loop.
  Valid outline/context persist before rendering, so conversion retry reuses them.
- Fixed PptxGenJS Node code renders native editable shapes/text from JSON, never
  model-generated JavaScript. Explicit text-capacity checks reject overflow.
  Cover/section/bullets/timeline/summary use editable text; two_column/risk_matrix
  use two-column text when no special visual data is present. There is no claim
  that arbitrary charts, images or full risk-matrix graphics are supported.
- Headless LibreOffice uses a unique private profile and finite timeout. Both
  outputs publish only after PDF conversion and exact page-count validation.
  Nginx serves PDF.js ES-module workers with the required JavaScript MIME type.
  UI exposes stages/progress, failure/retry, all-page preview and PPTX/PDF download.
  Files, jobs, metadata and aliases enforce owner scope before filesystem lookup.

Design/API contracts: [plan](../architecture/phase-5-plan.md),
[API](../api/phase-5.md), and regenerated `openapi.json`/frontend types.
The search adapter follows the [official Tavily search contract](https://docs.tavily.com/documentation/api-reference/endpoint/search).
Renderer notes and file output use the [PptxGenJS API](https://gitbrent.github.io/PptxGenJS/docs/speaker-notes.html)
and [file-saving contract](https://gitbrent.github.io/PptxGenJS/docs/usage-saving/).

## Actual acceptance results

| Check | Outcome |
| --- | --- |
| `.venv/Scripts/python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy (54 app files), 75 unit tests; integration separately executed |
| `.venv/Scripts/python scripts/dev.py export-api` | PASS: backend schema exported |
| `cd frontend; npm.cmd run api:types` | PASS: frontend contracts regenerated |
| `cd frontend; npm.cmd run check` | PASS: Prettier, strict TypeScript and api:check |
| `cd frontend; npm.cmd run build` | PASS: production bundle; presentation/PDF.js lazy loaded |
| `.venv/Scripts/python -X utf8 scripts/test_phase5.py` with environment below | PASS: 48 integration tests, 17 browser tests; real isolated migrations, Postgres/pgvector, Redis/RQ/Mailpit, restarts and dependency outage checks |
| `cd backend/renderer; npm.cmd audit --omit=dev` | PASS: 0 reported vulnerabilities after locked image-size override |
| `docker compose --profile app --profile mail up --build -d --wait` | PASS: normal stack healthy and migrated to 0006_presentations; queue empty before startup |
| Normal API missing-Key / static worker check | PASS: search returns actionable 503 with X-Request-ID; worker MIME is application/javascript; no external request |
| Git ignore / configured-secret scan / diff --check | PASS: private specification, secrets, runtime artifacts and tests remain excluded |
| Local fixed-renderer fixture | PASS: six Chinese editable slides, no model call |
| Edited-PPTX reopen and conversion | PASS: changed a native text shape, LibreOffice reopened it, PDF contains changed Chinese text and exactly six pages |
| Six-page PDF inspection | PASS: all pages nonblank, Chinese text and CJK font present; first page and contact sheet visually inspected |
| Ownership | PASS: foreign owner rejected by metadata, jobs, preview and download routes; empty foreign-owner listing |
| Failure/cache/idempotency | PASS: bad citations fail without downloadable files; missing LLM/search config gives 503; missing converter fails; conversion retry preserves outline and provider call count stays 1; repeated request reuses id, changed input on same key is 409 |
| Provider request contract | PASS: actual independent HTTP transport sees configured model, max_tokens=6000, reasoning_effort=minimal, stream=true and configured connect/read timeouts |

Final isolated suite evidence: `logs/phase-5-suite-final.log` (48 integration / 17
browser passed). Previous first browser run had 16 passes and one label-locator
timeout; it was not counted as a pass. An explicit accessible language label fixed
it. PDF.js worker MIME was identified by an actual HTTP response, corrected in
Nginx, syntax-checked and reloaded in the isolated frontend before final browser
verification; the normal final image includes the corrected file.

Exact runner environment:

```powershell
$env:MEMORA_TEST_FRONTEND_PORT='55273'
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:BUILDKIT_NO_CLIENT_TOKEN='1'
.venv/Scripts/python -X utf8 scripts/test_phase5.py
```

The runner uses `memora-phase5-test`, `memora_test` and disposable test volumes.
Only this isolated database runs Alembic upgrade → downgrade-to-base → upgrade
and schema-drift checks. It never uses metadata.create_all. The normal data/index
is preserved. Test HTTP providers run independently and are never selected by a
production fake-provider switch. Test sources/runners and generated evidence
remain local/ignored per the owner's publication preference.

PPTX acceptance checks unzip all six slide XML files, require native a:t text and
CJK font declarations, and inspect citation notes/URLs/retrieval times. Actual
LibreOffice 25.2.3.2 opens/converts the file; the edited text shape round-trip is
also checked. PyMuPDF verifies six nonblank PDF pages and their fonts; PDF.js
browser acceptance renders all six canvas pages and downloads the PPTX.
Runtime Node observed: v22.23.4. CJK face: WenQuanYi Zen Hei (fc-match verified).
Local artifacts: `data/phase5-preview.png`, `data/phase5-contact.png`,
`data/phase5-edit/edited.pptx`, `data/phase5-edit/edited.pdf`, and
`frontend/test-results/phase-5-preview.png` (all ignored).

## Real API request budget and pending live acceptance

**This Phase 5 implementation/acceptance made 0 real Gemini requests, 0 real
Embedding requests, 0 real Tavily requests and 0 external SMTP requests.**
Independent HTTP test fixtures supplied outline/search data; PostgreSQL, Redis,
RQ, Node, LibreOffice, PDFs and browser rendering were real. Local Mailpit traffic
belongs to regression tests and has no external relay. Do not confuse fixture
URLs/content with live search acceptance.

The preceding Phase 3 short-sample real extraction remains passed with one
Gemini request and no retry, as recorded in Phase 3/4 reports. It was not repeated.
Existing full Phase 1 live-model, Phase 2 real Embedding/RAG gates and two-real-
meeting Phase 4 temporal acceptance remain pending. Real Tavily search, real
Gemini six-slide outline quality and semantic faithfulness of generated claims
remain **pending**, because no new live verification was run. Source-ID validation
establishes provenance linkage, not complete semantic entailment of every claim.

## Build issues resolved

Initial apt/system dependency downloads timed out; an alternate HTTPS mirror was
not usable inside Docker (TLS EOF), so signature validation was never disabled.
Returned to Debian's standard signed repository, bounded apt retries/timeouts,
and switched the failed large Noto package to WenQuanYi CJK. LibreOffice/font
installation then completed. Python dependencies now have a separate build stage
matching the existing lock/cache, avoiding redownload when system packages change.
Node dependencies use a locked separate stage; production images exclude tests.
Final successful build record: `logs/phase-5-build-complete.log`; subsequent suite
builds reuse the completed system/dependency layers. No missing dependency was
reported as successful conversion.

## Configuration, startup and real verification procedure

Root `.env` stays ignored. `.env.example` contains blank credential placeholders.
There is exactly one SEARCH_API_KEY assignment; an old placeholder at line 66 is
reused rather than shadowed by an appended blank value.

| Setting | Exact line in .env and .env.example |
| --- | --- |
| SEARCH_API_KEY | 66 — fill local Tavily Key here |
| SEARCH_BASE_URL | 110 — https://api.tavily.com |
| SEARCH_MAX_RESULTS / SEARCH_TIMEOUT_SECONDS | 111 / 112 — 5 / 15 seconds |
| SEARCH_CACHE_TTL_SECONDS | 114 — 300 seconds |
| PRESENTATION_MAX_OUTPUT_TOKENS | 116 — 6000, applied to planning |
| PRESENTATION_JOB_TIMEOUT_SECONDS | 117 — 240 seconds |
| PRESENTATION_CONVERSION_TIMEOUT_SECONDS | 118 — 90 seconds |
| PRESENTATION_NODE / PRESENTATION_LIBREOFFICE | 120 / 121 — executable names/paths |
| Existing LLM model / Key / Base URL / reasoning | 19 / 21 / 23 / 73 — retained |
| Existing Embedding Key / Base URL / model / dimensions | 38 / 40 / 43 / 44 — retained, 768 dimensions |
| SMTP_MODE / SMTP_EXTERNAL_SEND_ENABLED | 95 / 102 — local / false |

Start/recreate after configuring secrets:

```powershell
docker compose --profile app --profile mail up --build -d --wait
```

Open http://localhost:5173. With Key absent, search/optional-web generation gives
an actionable configuration error. To do a minimal live check later: fill only
local line 66, recreate API/worker, search once on the Presentations page and
inspect actual URL/retrieval time. Reuse that query to benefit from its five-minute
cache, select a small ready PDF/meeting plus memory, choose six slides/language,
and generate once. Inspect citations, all six preview pages, download/edit the
PPTX and compare PDF page count. This is a manual pending procedure, not an
already passed live result. Avoid looping or automatically trying more queries.

For hybrid development, install renderer dependencies with npm ci inside
backend/renderer, LibreOffice and the CJK font, and configure executable paths.
The Linux container path is accepted; complete native Windows RQ/hybrid and
PowerPoint Desktop compatibility are not separately verified. PPTX fonts are
referenced rather than embedded. External TLS/auth SMTP and deliverability remain
untested/unauthorized. Fixed demo identity and production/public hardening are
outside Phase 5. Stop here; do not implement Phase 6.
