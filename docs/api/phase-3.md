# Phase 3 API and state contract

All paths start with `/api`, use server-owned demo identity, and return the
established error envelope and `X-Request-ID`. No model or SMTP credentials are
returned. Models below are exported into `openapi.json` and generated TS types.

| Method | Path | Contract |
| --- | --- | --- |
| POST | `/meetings/upload` | Multipart UTF-8 `.txt` `file`, optional ISO `date` and IANA `timezone`; 202 `{meeting_id,job_id,duplicate}` |
| GET | `/meetings` | Owned meeting summaries/status, newest first |
| GET | `/meetings/{id}/analysis` | Metadata, validated extraction, risks/tasks/drafts, job stage/progress and sanitized errors |
| GET | `/meetings/{id}/transcript` | Authorized original lines, 1-based numbers, speaker labels |
| GET | `/meetings/{id}/audit` | Scoped append-only meeting/task/email audit events |
| POST | `/meetings/{id}/retry` | `{date?,timezone?}`; only failed analysis creates a new job; active/ready returns original job |
| GET | `/jobs/{id}` | Existing persistent ingestion/meeting-job status contract |
| GET | `/tasks` | Filter `status`, exact `owner_name`, `meeting_id`, aware `due_before` |
| PATCH | `/tasks/{id}` | Partial `{title?,owner_name?,due_at?,status?}`; omitted fields preserved; UTC offset required for due_at |
| GET | `/emails` | Owned draft/delivery records |
| GET | `/emails/{id}` | Current revision, approval/delivery state and provider Message-ID |
| PATCH | `/emails/{id}` | `{revision,recipients?,subject?,body?}`; partial edit increments revision and clears approval; header injection rejected |
| POST | `/emails/{id}/approve-send` | `{revision,idempotency_key:UUID,confirm_send:true}`; 202 email outbox snapshot |

Email delivery is polled through `/emails/{id}`, not the document-backed `/jobs`
endpoint: its outbox row is the durable send job/claim. The approval response
identifies that email resource and its real queue/send state. No fake success is
returned for queue submission, SMTP absence or invalid recipients.

## Evidence and dates

TXT MIME is `text/plain` or generic `application/octet-stream` with `.txt`
extension and strict UTF-8 content validation. Optional BOM is removed for
parsing, but original bytes/checksum are preserved privately. Binary controls,
oversize input and insufficient context are explicit errors. Raw multipart
ingress is bounded before framework spooling, including chunked bodies.

Optional transcript headers: `Title:`, `Date:`, `Timezone:`, `Location:`. User
date/timezone fields take precedence. Date-only input retains `date_precision`
`date`; the normalized UTC midnight is a date anchor, not a fabricated meeting
start time. Relative deadlines require date and timezone. Unknown fields remain
null and/or review-required. Supported deadline normalization: ISO dates,
English full/abbreviated month dates, today/tomorrow and Chinese 今天/明天.
Other phrases remain unresolved and need review; no system-date assumption.

Extraction is Pydantic-validated: summary/topics/people/decisions, six risk
classes, severity/rationale/mitigation, proposed tasks and candidate facts.
Every person/decision/risk/task/fact has exact quoted source text, line offsets
and `explicit_fact`/`inference`/`unknown`. Invented source lines/quotes/owners/roles/
deadlines and invalid task-risk links fail validation. Model confidence is
descriptive, not a calibrated probability; evidence matching is structural,
not a proof that every generated interpretation is semantically correct.

Records are committed atomically after validation. Material risks lacking a
model-proposed linked task receive an explicit review proposal with unknown
owner/due date, never invented values. Candidate facts stay in analysis JSON;
no Phase 4 entity registry, semantic memory or fresh-chat recall is added.

## Idempotency, caching and retries

Upload uniqueness is owner/checksum/TXT. Repeated uploads do not requeue or create
new meeting/task/draft rows. Job claims and final publication are row-locked and
bound to the current job; failed/stale work cannot later publish success.
Decision/risk/task keys and one draft per risk also have database uniqueness.

Validated extraction is cached in private Redis, scoped by owner, source hash,
meeting date/timezone, model/Base URL/thinking and schema version. A commit
failure can retry from that validated cache without paying for another model
call. Cache contains private analysis/evidence; Redis volumes require the same
privacy treatment as the database. Successful ready meetings are never silently
re-extracted. Schema/evidence repair is at most once; transport retry/backoff
reuses the existing bounded provider policy. Chat and extraction share Redis
model admission slots in addition to the existing local semaphore. Embedding
configuration, vector profile and cache behavior remain unchanged; TXT is
excluded from PDF listing/retrieval and is never embedded in Phase 3.

Task statuses: proposed/open/in_progress/done/cancelled. Edits preserve original
evidence/due_text and audit owner/due/status before/after. They do not trigger
mail delivery or re-run extraction.

## Email authorization and delivery

Generated drafts have no inferred recipients. Medium/high risks create editable
plain-text drafts referencing evidence and linked proposed tasks. Save never
sends. Editing increments revision and sets awaiting_approval. In-flight, sent
or ambiguous emails cannot be edited/resubmitted.

Approval locks the exact current revision and records a persistent owner-scoped
idempotency key. Replaying any registered key does not enqueue again; a key
cannot be applied to another email/revision. Different repeated approval keys
on queued/sending/sent email also cannot trigger another send. Queue failures
are saved honestly. Only a fresh explicit approval may retry known non-delivery.

Worker claim commits `sending` before SMTP. Stable Message-ID includes email ID
and revision. All recipients are checked before DATA, so a known refusal cannot
cause intentional partial delivery. Only final SMTP acceptance leads to `sent`.
SMTP failure after DATA begins, crash after acceptance, or stale sending state
becomes `SMTP_DELIVERY_UNCERTAIN` / failed and requires mailbox reconciliation;
automatic resend is prohibited. This does not claim distributed exactly-once
SMTP delivery. QUIT/connection-close issues cannot cause replay of accepted mail.

Local mode restricts the host to loopback/Mailpit and recipients to an explicit
allowlist under `.test`/`.invalid`. Mailpit has no configured relay. External
delivery is disabled by default and additionally requires owner configuration,
TLS, exact allowlist and explicit revision approval. No external mailbox was
used in Phase 3 verification. Audits record identifiers, revisions, approval
keys, state transitions and provider IDs; no raw transcript or credentials.

Important errors include TXT_TYPE_REQUIRED/TXT_ENCODING/TXT_SIZE_LIMIT,
MEETING_DATE_REQUIRED/MEETING_CONTEXT_LIMIT/MEETING_INVALID_ANALYSIS,
MEETING_SOURCE_CHANGED, LLM_BUSY/LLM_ADMISSION_UNAVAILABLE, QUEUE_UNAVAILABLE,
SMTP_NOT_CONFIGURED/SMTP_EXTERNAL_DISABLED/EMAIL_RECIPIENT_NOT_ALLOWED,
EMAIL_REVISION_CHANGED/IDEMPOTENCY_CONFLICT/EMAIL_LOCKED and
EMAIL_RECONCILIATION_REQUIRED. Errors remain separate from infrastructure health.
