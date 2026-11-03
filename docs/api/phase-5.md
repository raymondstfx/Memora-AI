# Phase 5 API and output contracts

All endpoints are under /api with existing owner resolution, error envelope and
X-Request-ID. OpenAPI contains the exact schemas. Secrets are server-side.

| Route | Behavior |
| --- | --- |
| POST /search | query (2–500 chars), actual Tavily title/url/snippet/published_at?/retrieved_at, cached flag |
| GET /search/config | configured flag and actionable Key message, never returns credentials |
| POST /presentations/generate | request_key UUID, instruction, explicit slide_count 1–12, language en/zh, selected document_ids/meeting_ids, use_memories, optional web_query |
| POST /presentations | Compatibility alias for generate |
| GET /presentations | Latest 100 owned tasks |
| GET /presentations/{id} | status, stage, progress, attempts, page_count, outline_json, sources_json and job_id |
| GET /jobs/{job_id} | Scoped presentation task state; succeeded maps from ready |
| POST /presentations/{id}/retry | Explicit retry only after failure, at most 3 attempts, valid outline reused |
| GET /presentations/{id}/preview | Private PDF, only when both outputs ready |
| GET /presentations/{id}/download | Editable PPTX |
| GET /presentations/{id}/download.pptx or .pdf | Explicit format aliases |

Presentation public job_id equals presentation id; RQ has a separate execution
identifier. Document jobs retain their existing contracts and document FK.
Presentation status is queued/running/ready/failed; stages expose retrieving,
planning, rendering, converting and complete. Stale jobs are marked interrupted
on status reads; they never replay automatically. Request-key reuse returns the
same resource; changed input on the same key returns 409. Only one active task
per owner is admitted. Failed partial artifacts are never downloadable.

Outline separates content from executable renderer code: presentation_title,
theme=memora, language, slide_count, slides[]. Types are cover, section, bullets,
two_column, timeline, risk_matrix and summary. Each slide contains title,
1–6 bounded bullets, optional speaker_notes, visual_spec=none and source_refs.
Every source reference must exist in the retrieved context; sourced decks require
at least one reference per slide. Unsupported structures are rejected, not run.
Without special visual data, risk_matrix uses two-column text; timeline/section/
cover/summary use editable text layouts. Notes retain full evidence/citations;
visible footers contain short source labels. The model cannot supply JavaScript,
filesystem paths, remote assets or email instructions to the renderer.

Chat /search query explicitly selects search_web and grounds the answer using
validated source references. Citations persist their original URL and retrieval
time, including on cache hits. Ordinary chat never claims it searched the web.
The UI also exposes standalone search and optional web evidence on a deck.

Search sends a basic Tavily query with max_results, no generated answer, images
or raw content. A shared finite Redis admission lock and bounded response bytes
limit usage. Rate limiting/auth/provider failures return sanitized actionable
errors with no fabricated result or automatic retry. Search caches last up to
SEARCH_CACHE_TTL_SECONDS and are private to owner/endpoint/query profile.

Downloads use server-derived paths below private storage, safe fixed filenames,
private/no-store and nosniff. Ownership is checked before file lookup. LibreOffice
is bounded and gets a unique profile; PDF page count must match requested slides.
