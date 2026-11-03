# Phase 4 memory API

All paths use `/api`, the existing demo owner scope, UUIDs and UTC timestamps.
Failures preserve the standard code/message/request_id/details envelope and
X-Request-ID header. Authoritative schemas are in `openapi.json`.

| Method and path | Contract |
| --- | --- |
| GET /entities | Active canonical entities and confirmed/observed aliases |
| POST /entities/{id}/aliases | revision, alias, confirm_identity=true; other-entity collision is 409 |
| POST /entities/{id}/merge | revision, target_id, confirm_identity=true; same type required |
| GET /memories | entity_id, status, memory_type, valid_at with UTC offset, limit 1–200 |
| GET /memories/{id} | Value, event/recording times, state, revision and provenance |
| PATCH /memories/{id} | revision, value, reason, optional aware valid_from/subject_entity_id; append correction |
| DELETE /memories/{id}?revision=N | Soft revocation, 204; stale version is 409 |
| POST /memories/import-meetings?after=UUID | At most 200 saved ready meetings; next_cursor for continuation, no model calls |
| POST /memories/search | question; direct stored answer or full-text evidence candidates |

Memory identity is owner + source key. The key survives entity merge/correction
and prevents source replay from restoring suppressed facts. Owner writes serialize
on the owner row; publication and memory are one transaction. All mutation APIs
check ownership and explicit revision. Alias/merge/correction/revocation create
audit events without logging document contents.

`valid_from`/`valid_to` are half-open event-time intervals; observed_at is the UTC
recording time. Unknown dates/inferences stay needs_review. Same-time conflicting
values have no selected winner; later valid observations preserve older history.
Soft revoked/corrected rows retain tombstones and original evidence. Corrections
are labelled user_correction; old quotes do not prove a user's replacement value.

Chat stores search_memories tool metadata and citations in the existing message
record. Exact owner/deadline/time questions use scoped relational queries;
other recall uses GIN-indexed full-text candidates and the existing grounded
provider/checkpoint flow. A fresh conversation requires no previous thread state.
Citations identify meeting/document/memory IDs, occurred_at, source line range,
source type and current state, or explicit source chat/message IDs. PDF citation
fields remain populated as before; nullable fields support non-PDF evidence.

Embedding profiles, vectors and indexes are unchanged. Existing ready meetings
are only imported on explicit request; no automatic re-extraction or reindexing.
Import fails atomically on missing/changed private original evidence. Supported
legacy literal adapters are conservative English owner/deadline forms; general
meeting claims use the existing structured extraction schema and evidence checks.
