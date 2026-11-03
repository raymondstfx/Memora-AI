# Phase 2 API and index contract

Phase 2 extends the Phase 1 chat contract. All resource operations derive the
owner server-side, including downloads and jobs. Unknown/other-owner resources
return 404. HTTP errors retain `code`, `message`, `request_id`; stream errors use
the existing SSE envelope. Infrastructure health requires Alembic `0003_pdf`;
provider configuration is deliberately separate from infrastructure health.

| Method | `/api` path | Contract |
| --- | --- | --- |
| GET | `/documents/config` | Embedding readiness, missing variable names, model/dimension/profile and upload cap; never keys |
| POST | `/documents/upload` | Multipart `file`; PDF only; 202 `{document_id, job_id, duplicate}` |
| GET | `/documents` | Owned documents with processing status, page/chunk counts and errors |
| GET | `/documents/{id}` | Owned document metadata; incompatible ready indexes appear `needs_reindex` |
| GET | `/documents/{id}/file` | Authorized original PDF; source cards append `#page=N` |
| GET | `/jobs/{id}` | Owned job stage/status/progress/attempts/error |
| POST | `/documents/{id}/retry` | JSON `{reparse:false}`; reuse extracted chunks, retry embedding; `true` clears chunks and reparses |
| POST | `/documents/{id}/reindex` | JSON `{reparse:false}`; explicit new embedding profile, invalidate old vectors, rebuild |
| POST | `/documents/search` | `{question, document_ids?: UUID[]}`; hybrid evidence with vector/text ranks and scores |
| DELETE | `/documents/{id}` | 204; original file, jobs and dependent chunks/vectors removed |
| POST | `/chat/stream` | Existing body now accepts up to 5 owned ready PDF UUIDs in `attachments` |

## Ingestion state and retry

Document states are `queued`, `processing`, `embedding`, `ready`, `failed` and
the derived `needs_reindex`. Jobs are `queued`, `running`, `succeeded`, `failed`;
stages identify extraction vs embedding. A 202/queued job is not indexing success.
Only the transaction that stores all validated vectors marks a document ready.
Database claiming/current-job guards prevent repeated queue delivery or stale
workers from duplicating chunks or resurrecting failed jobs.

Limits cover the incoming multipart body (including chunked transport), actual
file size, extension/MIME/header, parser subprocess duration/memory on Linux,
pages, extracted text, chunks, embedding batches and active jobs per owner.
Private paths use UUIDs, not client filenames; display/download names are
sanitized. Duplicate `(owner, SHA-256, PDF)` uploads reuse the existing document
and job. A duplicate failed document requires explicit retry.

Native PDF parsing is asynchronous in Redis/RQ. Queue payloads use JSON and UUIDs;
credentials and document text are not serialized into jobs. Corrupt/repaired,
encrypted, scanned/empty and partially textless PDFs fail clearly; no OCR or
silent partial success. Text extraction/chunks are cached independently from
embedding. Missing embedding settings leave the document failed with
`EMBEDDING_NOT_CONFIGURED`, while retaining valid extracted chunks for retry.

Provider errors are sanitized and bounded. HTTP 429/502/503/504 retries have
bounded backoff; timeouts and other failures require explicit job retry. Vector
count, ordering, dimensions, finiteness and nonzero norm are validated before a
complete index is committed. Queue outages and worker timeouts have explicit
failure records. Polling an expired queued/running job reconciles it to failure;
the UI never treats an expired or partially completed index as ready.

## Embedding profiles and retrieval

An index profile hashes provider + normalized API Base URL + model + dimensions.
Changing any of these makes old ready indexes incompatible. API keys are not part
of the fingerprint, so key rotation alone does not require a rebuild. Selected
incompatible indexes produce 409 `INDEX_PROFILE_MISMATCH`; unscoped search does
not silently mix them. Model/dimension changes require explicit reindexing.

The pgvector column stores variable-dimension vectors, with matching profile and
dimension metadata. Search filters owned ready documents and matching chunk
profiles before exact cosine ranking. Full-text retrieval uses a GIN-indexed
Postgres `tsvector` with deterministic English/CJK lexical segmentation. RRF
fuses both rankings; exact ties prefer full-text rank, then vector rank and ID.
The small demo uses exact search; ANN indexing is deferred until corpus size
justifies a profile-specific index. Chunk token counts are deterministic
approximate English-word/CJK-character units, not a provider tokenizer guarantee.
Page boundaries are never crossed; overlap, page number, ordinal and text hash
remain attached to each chunk. Evidence excerpts are bounded and centered around
matched query terms where possible.

## RAG and citations

PDF IDs are validated before the user turn commits. Retrieval occurs after the
question is persisted and emits real `tool_start`/`tool_result` activity. PDF
evidence is lower-trust data. Only document search is enabled; text cannot invoke
email, external search, filesystem tools or later-phase effects.

Grounded model output must be JSON with `answer`, `source_refs` and optional
`insufficient_evidence`. Source IDs must come from this request's retrieved
chunks, occur inline, and agree with the reference list. One bounded schema repair
is allowed; invalid citations fail without exposing or saving an accepted answer.
Validated IDs are rendered as `[1]` labels and persisted source cards containing
filename, page, chunk ID and excerpt. Reload preserves citations. A lack of
evidence yields an explicit non-answer, never an invented PDF fact.

Ordinary chat retains true upstream token streaming. PDF answers are buffered for
grounding/citation validation, then streamed with `citation` events and validated
text. LangGraph/Postgres checkpoints are used for model calls in both flows.
Phase 1 real-model and Phase 2 real-embedding/RAG acceptance remain pending real
credentials; passing independent test providers is not a real-provider gate pass.

References: [OpenAI embeddings contract](https://developers.openai.com/api/reference/resources/embeddings/methods/create),
[RQ workers](https://python-rq.org/docs/workers/),
[PyMuPDF document API](https://pymupdf.readthedocs.io/en/latest/document.html).
