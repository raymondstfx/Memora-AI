# Phase 5 plan

Keep the modular monolith and existing provider/Redis admission boundaries.
Add a Tavily search adapter with bounded results/bytes/time, no automatic retries,
per-owner hashed cache keys and original retrieved_at. Explicit /search chat and
presentation opt-in use actual results only. Evidence cannot invoke tools.

Add scoped presentation task state via Alembic, request idempotency, one active
job per owner, bounded RQ execution and explicit finite retry. Retrieve selected
ready PDFs and checksum-verified meetings plus owned memories and optional web.
Generate a strict outline with exact count/language and validated source keys.
Persist valid outline/context before rendering so conversion retry avoids another
model call. Missing configuration and invalid output are explicit failures.

A fixed Node/PptxGenJS renderer reads JSON only and writes real editable shapes.
Cap titles/bullets, reject overflow, use documented bullet/two-column fallbacks
for variants without visual data. LibreOffice uses a unique private profile and
converts to PDF with an exact page-count check. Publish only when both outputs
are valid. Scope all metadata, job, preview and download routes by owner.

Install CJK fonts in runtime; PDF.js renders all pages. Verify with independent
providers, real isolated PostgreSQL migrations, Redis/RQ, LibreOffice and browser
checks. No real search Key is currently configured; live search and real model
slide quality stay gated. No Phase 6 work or external SMTP.
