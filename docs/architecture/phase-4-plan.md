# Phase 4 plan

Add owned entities/aliases, evidence-linked entity relations and append-only fact
versions with valid/observed times. Normalize exact names using Unicode/case/space
normalization; identity aliases/merges require explicit human confirmation.
Meeting publication writes validated structured claims and conservative source
patterns atomically. Import existing ready meetings without new model calls.
Corrections append versions, revocation retains suppression tombstones; imports
must never resurrect corrected/deleted facts. Out-of-order meetings recompute
validity in event-time order; same-time contradictory facts require review.

Use indexed Postgres full-text plus exact entity/temporal SQL for retrieval.
Precise owner/deadline answers are rendered from stored records with meeting/line
citations; generic grounded synthesis uses the existing model/checkpoints and
bounded provider policy. No new Embedding calls/index rebuilds are needed.
Memory Center supports filtering, provenance, corrections/revocation and explicit
entity alias/merge controls. No Phase 5 search/presentation behavior.

Verify the Nov 2/Nov 4 API owner/deadline timeline in a new conversation, both
meeting citations, corrections/revocations, conflicts, out-of-order ingestion,
scope/idempotency, real migrations/restarts and browser workflows. Test providers
stay independent/local; the preceding real Phase 3 recheck is capped at two calls.
