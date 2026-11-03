# Phase 4 delivery and verification

Date: 2026-11-03, Asia/Shanghai. Scope: Phase 4 only. Phase 5 has not started.
No commit or push is performed for this request. The private specification stays
ignored. Read AGENTS.md, the authoritative implementation specification, current
code and the Phase 3/latest provider reports before implementation.

## Delivered behavior

- Migration `0005_memories` adds owned UUID/UTC entities, aliases, memories and
  source-bearing entity relations. Postgres GIN full-text and owner/slot/event-time
  indexes support retrieval. Existing PDF vector profiles/indexes are unchanged.
- Exact NFKC/case/space normalization; similar names and titles remain distinct.
  Alias creation and same-type entity merges require explicit identity confirmation
  and current revisions. Merges retain original evidence and recompute conflicts.
- Meeting publication atomically saves validated semantic claims and dated episodic
  decisions/risks/commitments. Existing ready meetings can be explicitly imported
  from saved extraction plus checksum-verified private originals, at most 200 per
  batch with continuation cursor. Missing/changed originals fail atomically.
  No extra extraction, Embedding call or automatic index rebuild is involved.
- Atomic subject/predicate/value facts include event and recording times, source
  identifiers, exact quotes and line ranges, confidence, review/lifecycle state.
  Unknown dates and inferred claims remain review-required. Out-of-order events
  rebuild half-open valid intervals. Same-time contradictions have no winner.
- Corrections append reason-bearing versions, retaining originals and provenance.
  DELETE revokes from recall while retaining suppression/history. Source keys and
  tombstones prevent imports/retries from resurrecting corrected or revoked facts.
  Audit records contain identifiers/state, not document text or credentials.
- Cross-conversation `search_memories` uses scoped relational/time queries for
  precise owner/deadline questions and indexed full-text candidates for other
  recall. Exact answers render stored facts; general synthesis uses the existing
  grounded provider/LangGraph path. Tool metadata and dated citations persist in
  messages. Missing/ambiguous/conflicting records produce an honest explanation.
- Memory UI supports entity/status/type/effective-time filters, source links,
  corrections, revocation, and explicit identity controls. Chat supports opt-in
  `Remember:` assertions; ordinary dialogue/assistant guesses are not promoted.
  PDF citations and existing chat/document/meeting/task/mail contracts are retained.

See [implementation plan](../architecture/phase-4-plan.md) and
[API contract](../api/phase-4.md). OpenAPI and frontend types were regenerated.

## Phase 3 real extraction recheck

**Passed**, one real external request with existing Gemini configuration:
`gemini-3.1-flash-lite`, reasoning_effort=minimal, stream=true, max_tokens=3000,
HTTP 200. Verification-specific provider retries/schema repairs were zero; the
allowed extra retry was unused. No further live model tests were run.

Persisted evidence checks passed: three people, one decision, one risk, three
proposed tasks, correct ownership, exact quote/line validation, meeting date
Nov 2 Asia/Shanghai and Alex's Nov 5 task deadline (Nov 4 16:00 UTC). Drafts
remained unapproved with no recipients. The source was copied from host private
storage to the container private volume and checksum-verified, as the two
storage modes use distinct roots. Sanitized local record:
`logs/phase-3-live-recheck.json`. The earlier HTTP 503 remains historical in the
[Phase 3 report](phase-3.md), which now includes this successful follow-up.

**This task's real external request totals: Gemini 1, retries 0, Embedding 0,
external SMTP 0.** Local test SMTP traffic is separate and uses Mailpit only.

## Verification record

Run from the repository root with its Python 3.13 virtual environment. On Windows,
use npm.cmd. Browser tests use installed Edge; test ports/project/volumes are
isolated from local runtime data and all provider traffic is directed to independent
test fixtures. No production fake-provider switch exists.

| Exact command/check | Result |
| --- | --- |
| `.venv/Scripts/python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy (49 app files), 68 unit tests; integration intentionally separate |
| `.venv/Scripts/python scripts/dev.py export-api` | PASS: exported final backend schema |
| `cd frontend; npm.cmd run api:types` | PASS: generated frontend contracts |
| `cd frontend; npm.cmd run check` | PASS: Prettier, strict TypeScript and api:check |
| `cd frontend; npm.cmd run build` | PASS: production Vite bundle |
| `.venv/Scripts/python -X utf8 scripts/test_phase4.py` with environment below | PASS: 45 integration tests and 15 browser tests; migrations, restarts, outages and local SMTP regressions passed |
| `docker compose --profile app --profile mail up --build -d --wait` | PASS: normal stack healthy, upgrade to 0005_memories, local SMTP, external=false |
| Local ready-meeting import, repeated import, fresh SSE chat and saved history | PASS: 1 real-extracted saved meeting → 6 memories, second import inserts 0; fresh chat answers Alex with persisted meeting citation, 0 external calls |
| Git ignore and local credential scan | PASS: .env/private spec/tests/runtime logs ignored; configured provider secrets absent from 121 public candidate files |
| `git -c safe.directory=D:/Demo diff --check` | PASS |

Isolated runner environment:

```powershell
$env:MEMORA_TEST_FRONTEND_PORT='55273'
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:BUILDKIT_NO_CLIENT_TOKEN='1'
.venv/Scripts/python -X utf8 scripts/test_phase4.py
```

The runner includes real Postgres upgrade/downgrade-to-base/upgrade and Alembic
schema-drift checks, pgvector, Redis, RQ, Mailpit, Nginx/API, dependency outages,
restart persistence, integration and browser regression tests. Destructive
migration reversals run only against `memora-phase4-test` / `memora_test`.
No metadata.create_all fallback is used. Local verification sources remain
ignored on disk per the owner's repository publication preference.

Final run: `logs/phase-4-complete.log` records 45 passed integration tests and
15 passed browser tests, including the complete memory correction/revocation
workflow. Browser artifact: `frontend/test-results/phase-4-memory.png`.

Core acceptance covered by independent-provider integration tests: fresh chat
identifies Alex, reports Nov 5 → Nov 8 and cites both dated meeting sources;
reverse upload order produces the same timeline; supersession and valid-at
filters preserve old values; same-time conflicts, confirmed aliases/merges,
correction/revocation/reimport, user scope, stale revisions, full-text retrieval,
explicit chat-source memories, and persisted tool/citation records. Restart
probes compare exact memory IDs, values and sources without replay.

Earlier verification failures were fixed: Windows blocked default port 55173
(use 55273); the new test initially omitted its meeting fixture import; browser
checks needed to navigate back to Chat, wait for the newly uploaded meeting's
own ready state, and await filter refresh before asserting a unique revoked row.
These failures were not counted as passes and did not call Gemini.

## Configuration and operation

No new LLM/Embedding settings or index rebuild are required. Root `.env` and
`.env.example` have matching line numbers; only `.env` contains local secrets.

| Setting | File line |
| --- | --- |
| LLM_MODEL / LLM_API_KEY / LLM_BASE_URL | 19 / 21 / 23 |
| LLM_REASONING_EFFORT | 73 (minimal, retained) |
| EMBEDDING_API_KEY / EMBEDDING_BASE_URL | 38 / 40 |
| EMBEDDING_MODEL / EMBEDDING_DIMENSIONS | 43 / 44 (gemini-embedding-001 / 768, retained) |
| SMTP_HOST / SMTP_PORT / optional username/password | 67 / 68 / 69–70 |
| SMTP_MODE / SMTP_DOCKER_HOST | 95 (local) / 97 (mailpit) |
| SMTP_EXTERNAL_SEND_ENABLED | 102 (false) |
| Mailpit SMTP / web port | 104 / 105 (1025 / 8025) |

Start with the Compose command above, open http://localhost:5173, select Memory,
and explicitly import saved ready meetings if needed. New meeting analyses save
memories automatically in the publication transaction. Select All history to
inspect superseded/corrected/revoked records. Alias/merge actions require a
confirmation checkbox. Corrections save a reason and a new version; revocation
requires explicit UI confirmation. Mail capture is at http://localhost:8025.
External mail stays disabled; per-draft explicit approval remains required even
for local sending. No email was sent during the live extraction or memory import.

## Remaining limits / pending items

- The two-meeting temporal acceptance uses independent test extraction. Real
  Gemini passed one short meeting; a two-real-meeting end-to-end extraction and
  temporal synthesis run is **not performed**, to conserve quota. Normal fresh
  chat recall from the saved real extraction is verified without a model call.
- Full Phase 1 live-model and Phase 2 real Embedding/RAG gates remain pending;
  earlier bounded smoke results do not claim those broader gates passed.
- Broad multilingual/ambiguous natural-language extraction accuracy is not
  established. Legacy adapters support conservative English literal forms;
  general structured claims remain subject to model interpretation. Exact quotes
  and dates are checked, but this cannot prove every semantic interpretation.
- Memory recall uses SQL/full-text, without a new semantic vector index. General
  memory synthesis with the real Gemini model was not separately exercised.
- Revocation is a logical deletion and evidence remains inspectable. This is not
  physical erasure or a production retention/privacy policy. Demo user scope is
  retained; public authentication and production multi-user hardening are later.
- External SMTP TLS/auth/deliverability is untested and unauthorized. Native
  Windows RQ/hybrid bind-mount end-to-end acceptance remains unverified.

Stop after Phase 4; do not enter Phase 5 or push without owner approval.


## Repeat-request status check — 2026-11-03

The repeated Phase 4 request was checked against the implemented code, private
specification and existing acceptance records. No live model request was repeated.
Read-only/local API checks confirmed the saved real meeting remains ready with
three people, one risk, three task proposals, the correct Alex/Nov 5 task date,
unapproved empty-recipient drafts, and owner recall linked to the same meeting.
SMTP remains local and external sending false. The previous isolated acceptance
log still records 45 integration and 15 browser tests passing; these are previous
run results, not a newly executed full suite. This check used zero Gemini,
Embedding or SMTP requests. Fixed the stale AGENTS.md sentence saying Phase 4
was unimplemented. Three existing implementation commits remain local; the
subsequently authorized push failed on GitHub connection timeout. Phase 5 is
not started; no new push was attempted by this repeated implementation request.
