# Phase 3 implementation plan

Extend the existing monolith with scoped meetings, decisions, risks, tasks,
email outbox and append-only audit records. TXT originals use private Document
storage and existing Job/RQ infrastructure; no Embedding/profile changes.
Extraction is schema/evidence validated before one atomic business-data commit.
Candidate facts remain in meeting analysis JSON; Phase 4 semantic memory is not
implemented. Upload checksum and row locks prevent duplicate analysis effects.

SMTP is behind an application service. Editing a draft invalidates approval;
approval binds the exact revision, explicit confirmation and idempotency key.
Only the approval endpoint enqueues sends. Sending is claimed once in a durable
transaction before SMTP. Transport ambiguity becomes reconciliation-required,
never automatic resend. Local Mailpit has no external relay; real SMTP is disabled
by default, requires explicit owner configuration and exact recipient allowlist.
Audit records contain identifiers/states, never transcript or credential bodies.

Verify schemas/date/evidence boundaries, real Postgres migrations and ownership,
duplicate uploads/retries/approval races, local SMTP delivery and ambiguous
transport, browser upload/edit/approve/reload, existing regressions and builds.
One synthetic live Gemini extraction only after keyless checks; count requests.
Test sources remain local/ignored under the owner's publication policy.
