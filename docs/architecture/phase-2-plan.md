# Phase 2 plan and boundaries

Scope: PDF upload/validation, private storage, RQ asynchronous parsing/chunking,
embedding adapter, pgvector + full-text retrieval, chat grounding/citations,
status/retry/reindex UI and real credential-independent verification. No meeting,
task, email, memory extraction or Phase 3 functionality.

Alembic owns documents/chunks/jobs. Each user row is scoped. Upload is size/MIME/
extension/header checked and SHA-256 deduplicated. The parser runs with a process
timeout, page/text/chunk caps and per-page provenance. Unsupported encrypted,
corrupt or textless/partially textless PDFs fail clearly. No OCR is introduced.

Redis/RQ queues UUIDs using JSON serialization; no document text or credentials
are queued. Database job claiming and per-document current-job IDs prevent
duplicate effects. Queue failures and killed/timed-out workers have explicit
failure/retry paths. Extraction commits cached chunks before embedding; embedding
failure never produces ready status. Retry can reuse extracted chunks; reparse
is an explicit option. Document deletion removes original and dependent chunks.

An embedding profile hashes provider + Base URL + model + dimensions. Each ready
document/chunk records it. Vector columns allow explicit dimension changes without
schema mutation; exact scoped vector search is fused with indexed full-text ranks
using reciprocal rank fusion. No ANN index is needed for this small demo corpus.
Retrieval fails on incompatible selected indexes. Explicit reindex removes old
vectors and rebuilds with the new profile; no mixed-profile search is allowed.

Chat accepts owned ready PDF IDs. Retrieval occurs after the question is saved,
emits actual tool activity, and supplies untrusted evidence to the model. RAG
answers are buffered until validated structured JSON references only retrieved
chunk IDs, then streamed with application-issued citation cards. Unknown citations
fail rather than becoming fake source links. Insufficient evidence produces an
honest non-answer without calling the LLM. Ordinary Phase 1 chat keeps token SSE.

Tests use real Postgres/pgvector/FTS, Redis/RQ and native PDF parsing. A separate
test-only HTTP provider supplies embeddings and grounded structured answers; it
is excluded from production images. Real Phase 1 model acceptance and Phase 2
embedding/RAG acceptance remain pending the owner's credentials. Stop at Phase 2.
