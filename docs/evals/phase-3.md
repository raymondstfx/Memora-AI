# Phase 3 delivery and verification

Date: November 3, 2026 (Asia/Shanghai). Original Phase 3 delivery record;
Phase 4 is separately authorized and reported.
No commit/push or external email delivery is performed by this implementation.

## Status

Implementation and credential-independent acceptance are complete.
**Real short-sample Gemini extraction now passes** in the bounded follow-up below
(one HTTP 200 request, no retry). The original delivery attempt returned HTTP 503;
that historical failure is retained in this report. Neither run sent SMTP mail
or called Embedding.
Previous Gemini chat/RAG smoke results are preserved separately; this does not
turn the pending full Phase 1/2 live gates into passes.

The authoritative private specification, AGENTS.md, current code and latest
Gemini/Phase 2 reports were read. The implementation plan and API/state contract
are in [phase-3-plan](../architecture/phase-3-plan.md) and
[phase-3 API](../api/phase-3.md). The private specification remains ignored.

## Delivered scope

- Modular FastAPI services and React Meetings / Tasks & Actions pages, generated
  OpenAPI types, real RQ work, honest loading/empty/error/retry/status states.
- Migration `0004_meetings` adds seven scoped UUID/UTC tables: meetings, decisions,
  risks, tasks, email_outbox, email_approvals, audit_events. Existing Document/Job
  storage is reused for private TXT and jobs; no metadata.create_all workaround.
- UTF-8/BOM TXT validation, MIME/extension/size/context guards, raw multipart
  ingress bound before spooling, original checksum verification, numbered source
  lines and speaker labels, optional metadata headers/user date/timezone.
- Exact quoted evidence and offsets, strict extraction schema, explicit/inferred/
  unknown facts, six risk classes and justified severity, owners/deadlines that
  are never invented, review flags and bounded date normalization. Date-only
  metadata has precision `date`; UI says the start time is unknown.
- One atomic publication of validated decisions/risks/tasks/drafts. Material risks
  without a linked extracted task get a review proposal with unknown owner/due.
  Original evidence/due text and audit history remain after task edits.
- Owner/checksum/TXT upload dedupe, scoped unique business keys, job/current-job
  row locks and persistent approval keys. Duplicate upload, retry, repeated
  approval and worker execution do not duplicate tasks or accepted mail.
- Validated private analysis cache reused after a failed DB commit. Existing
  model retry policy is bounded; schema repair is at most once. Chat/extraction
  share Redis admission slots. Gemini/Embedding settings and vector profile stay
  unchanged; TXT is excluded from PDF listing and all-document PDF retrieval.
- Editable plain-text drafts with explicitly chosen allowlisted recipients.
  Save invalidates approval; a checked explicit approval binds the exact revision.
  SMTP is disabled by default. External transport also requires owner configuration
  and TLS; no external email was authorized or sent.
- Durable sending claim before SMTP, all-recipient preflight before DATA, stable
  Message-ID, SMTP result and audit. A known non-delivery needs fresh explicit
  approval to retry. Lost acknowledgment, stale sending or post-acceptance crash
  requires reconciliation; automatic resend is blocked. This is conservative
  SMTP ambiguity handling, not a distributed exactly-once delivery claim.
- No Phase 4 entity registry, semantic memory or cross-session memory retrieval.
  Extracted candidate facts remain in meeting analysis JSON only.

## Checks actually run

Commands use Windows `.venv\Scripts\python` / `npm.cmd`. Test providers, fixtures,
browser tests and runners are local/ignored under the owner's publication policy;
they exist in the verified workspace, not a fresh public checkout. Production
images exclude `backend/tests`; no production fake-provider fallback exists.

| Check | Result |
| --- | --- |
| `python scripts/dev.py check` | PASS: Ruff formatting/lint, strict mypy on **46 application files**, **65 unit/contract tests**; integration tests intentionally excluded here |
| Final `python scripts/test_phase3.py` | PASS: **37 integration tests + 14 Playwright tests**, actual PostgreSQL/pgvector, Redis, RQ and local Mailpit |
| Same isolated runner | PASS: real upgrade → downgrade to base → upgrade, Alembic drift, dependency outage/recovery, PDF/chat restart persistence |
| Meeting-specific restart probe | PASS: meeting/task/risk/draft/audit IDs survive API/Postgres/worker restart, job attempts remain one, no replay |
| `python scripts/export_openapi.py` / `npm run api:types` | PASS: backend schema and frontend contract regenerated |
| `npm run check` / `npm run build` | PASS: Prettier, strict TypeScript, generated-type freshness, Vite build; Linux frontend/backend images also build |
| `docker compose --profile app up --build -d --wait` | PASS: normal API/frontend/Postgres/Redis/worker healthy; migration exits 0; SMTP remains disabled |
| Real Gemini extraction | **FAILED / pending**: exactly 1 attempted request, HTTP 503, no retry/repair/fallback; no business records or email created |
| External SMTP / live mailbox delivery | **NOT RUN**: no owner authorization; disabled by configuration |

Final isolated command:

```powershell
$env:BUILDKIT_NO_CLIENT_TOKEN = '1'
$env:PLAYWRIGHT_CHANNEL = 'msedge'
$env:MEMORA_TEST_FRONTEND_PORT = '55273'
.venv\Scripts\python scripts/test_phase3.py
```

The project `memora-phase3-test` uses disposable volumes and its own ports.
Mailpit is `axllent/mailpit:v1.27`, verified image digest
`sha256:e22dce5b36f93c77082e204a3942fb6b283b7896e057458400a4c88344c3df68`.
No relay is configured. SMTP test recipients were only `demo@example.test`.
The runner cleans its containers, volumes and independent fixture HTTP process;
normal development volumes remain. Raw output is retained in ignored
`logs/phase-3-acceptance.log` / `logs/phase-3-startup.log` and browser screenshots
under ignored `frontend/test-results/`.
Final output contains `37 passed in 22.70s`, `14 passed (29.7s)`, the
meeting-specific restart PASS marker and the Phase 1/2/3 fixture acceptance PASS
markers. The Phase 3 actions screenshot was visually inspected; it shows a saved
task and an approved/sent local capture with the send controls locked afterward.

An intermediate browser assertion used the old subject as a locator after
editing that subject. It was corrected to select the same email region without
depending on editable text. An earlier yearless date-parser warning was fixed by
anchoring the meeting year explicitly. Final results are from actual runs after
fixes, not inferred from a build.

## Acceptance evidence

| Area | Verified evidence |
| --- | --- |
| A06/A07 | Parsed metadata/people/decisions, exact line quotes and justified schedule risk through real RQ/API/browser with independent extraction fixture |
| A08 | Proposed scoped task with Alex and normalized deadline; status/filter/edit operations preserve evidence; partial patches preserve omitted fields |
| A09 | Draft references risk, evidence and task; recipient/subject/body editable; unsaved edits cannot be approved |
| A10 | Explicitly approved email reaches actual local Mailpit; SMTP acceptance timestamp and Message-ID stored |
| A11/A22 | Parallel duplicate approvals and three competing send workers produce one captured message; repeated uploads/retries keep one task/draft |
| Cache | Failed business commit leaves no partial records; explicit retry reuses validated extraction with only one provider call |
| Failure | Invalid JSON/evidence fails atomically after bounded repair; queue failure and modified source bytes become failed states |
| A19 | Meeting/task/risk/draft/audit records survive real restarts without reprocessing |
| A20 | Foreign owner cannot get/edit meeting, transcript, task or email; list/filter scope is enforced |
| A21 | Transcript instruction to send to an attacker cannot approve mail; recipient list remains empty and SMTP inbox unchanged |
| SMTP ambiguity | Test delivers once to Mailpit then simulates lost acknowledgment; record becomes uncertain and another approval is blocked |
| Approval integrity | Editing increments revision; stale approval and key reuse across revision/resource are rejected; sent/in-flight/uncertain drafts are locked |
| Type isolation | Ready TXT meetings never enter PDF search candidates or change Embedding indexes |

## Exact configuration and startup

Root `.env` and `.env.example` have matching positions. Real keys/passwords belong
only in ignored `.env`; examples contain blank credential placeholders.

| Setting | Line | Purpose/default |
| --- | --- | --- |
| SMTP_HOST | 67 | Host API uses `127.0.0.1` for local capture |
| SMTP_PORT | 68 | 1025 local SMTP port |
| SMTP_USERNAME / SMTP_PASSWORD | 69 / 70 | Optional backend-only credentials, blank |
| DEMO_ALLOWED_RECIPIENTS | 71 | Exact comma-separated allowlist, demo@example.test |
| MEETING_MAX_UPLOAD_BYTES / MEETING_MAX_INPUT_BYTES | 88 / 89 | 65536 / 8000 byte guards |
| MEETING_MAX_OUTPUT_TOKENS | 90 | 3000, applied only to meeting requests |
| MEETING_REPAIR_ATTEMPTS | 92 | At most one schema/evidence repair |
| SMTP_MODE | 95 | originally disabled; Phase 4 local-capture default |
| SMTP_DOCKER_HOST | 97 | mailpit for container workers/API |
| SMTP_FROM | 98 | Explicit memora@example.test sender |
| SMTP_SECURITY | 99 | none only for local capture; starttls/ssl supported for external configuration |
| SMTP_TIMEOUT_SECONDS | 100 | 10 seconds per SMTP operation |
| SMTP_EXTERNAL_SEND_ENABLED | 102 | false; keep false during local verification |
| MAILPIT_SMTP_PORT / MAILPIT_HTTP_PORT | 104 / 105 | Loopback 1025 / 8025 |

Existing Gemini model/Key/Base URL/thinking stay at lines 19/21/23/73; Embedding
Key/Base URL/model/dimensions stay at 38/40/43/44. No reindex was performed.
Shared Compose environment passes all new backend controls to API and worker;
SMTP_DOCKER_HOST intentionally maps to their SMTP_HOST. Local backend reads the
same root `.env` directly.

Normal startup: `docker compose --profile app up --build -d --wait`.
For local capture only, set SMTP_MODE=local, keep SMTP_EXTERNAL_SEND_ENABLED=false,
SMTP_SECURITY=none and test allowlist, then:

```powershell
docker compose --profile app --profile mail up --build -d --wait
```

Open localhost:5173 and the Mailpit inbox at localhost:8025. Upload a dated TXT,
review evidence/tasks, edit/save the email, explicitly approve its saved revision
and inspect the captured message. Saving/uploading/retrying analysis never sends.
Do not configure a real external inbox or transport for this acceptance run.

## Live request record and remaining limits

`logs/phase-3-live-extraction.json` records the one synthetic call: model
`gemini-3.1-flash-lite`, reasoning_effort `minimal`, stream true, max_tokens 3000,
HTTP **503**, application code `PROVIDER_HTTP_ERROR`. LLM retries and extraction
repairs were set to zero for that verification only. Keys/prompts/quotes/generated
content were not logged. The model was not tried again. No real Embedding or
SMTP call accompanied it. Real meeting extraction quality therefore remains
unverified; account quota/availability is not claimed fixed.

Native Windows RQ execution and the full hybrid bind-mount flow are not separately
accepted; Linux container RQ is the verified path. External TLS/auth SMTP and
external inbox deliverability remain untested and unauthorized. SMTP uncertainty
requires manual mailbox reconciliation; there is no automatic retry or claim of
exactly-once delivery across the database/SMTP boundary. The fixed demo identity
and loopback deployment remain; no public authentication is added.

Date normalization intentionally supports a bounded set of phrases, not arbitrary
natural-language scheduling. Other dates remain unknown/review-required. Quote
validation prevents fabricated evidence IDs/offsets, not all possible semantic
misinterpretation. Candidate facts have no Phase 4 recall/normalization behavior.
Stop at Phase 3 until the owner explicitly requests the next phase.


## Bounded live follow-up — 2026-11-03

The owner authorized a short real extraction recheck, capped at two requests.
This follow-up **passed with one request**, no retry or schema repair: configured
`gemini-3.1-flash-lite`, `reasoning_effort=minimal`, streamed HTTP 200, max_tokens
3000. The original HTTP 503 record above remains historical evidence.

The persisted synthetic meeting contains three named people, one decision, one
risk and three task proposals. Original-line evidence validation passed; the
meeting date is 2026-11-02 Asia/Shanghai (2026-11-01 16:00 UTC), and Alex's explicit
Nov 5 deadline is correctly stored as 2026-11-04 16:00 UTC. Names, task ownership,
dated task rows and unapproved/no-recipient draft state were checked after commit.
The original fixture was checksum-verified in private container storage for
memory import. No secrets, document text or model response were written to logs.
Sanitized local evidence: `logs/phase-3-live-recheck.json`.

Request counts for this follow-up: Gemini 1, retries 0, Embedding 0, SMTP 0.
Real short-sample structured extraction acceptance is now passed. Broader
extraction quality and external mail remain unverified. Phase 4 work is separately
authorized and reported in `phase-4.md`; the earlier Phase 3 boundary text refers
to its original delivery.
