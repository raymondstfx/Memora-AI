# Memora AI local operator runbook

**当前状态（2026-11-04）：** 本地最终修复版已加载，默认中文，可持久切换 English。
第二次真实会议和跨会话时间变化问答通过；真实 PPT 内容仍失败，守卫拒绝发布。
本轮 Gemini 3 次，其余外部服务 0 次；保留全部配置、数据与索引。
以[最终验收与中文演示](evals/final-acceptance.md)为准。下方旧日期说明保留为历史。

### 本次缓存镜像更新说明

服务已运行，直接打开网页即可，不必再次请求注册表。最后一次完整构建因 Docker Hub 连接超时失败；
本次在依赖完全未变且本地已有验证镜像的前提下，用临时 Dockerfile 只复制最终后端源码及经检查的 Vite 静态产物，
然后执行 `docker compose --profile app --profile mail up -d --no-build --wait`。源码指纹、静态资源、健康与数据保留均已核对。
临时文件及构建证据在本地 `logs/`，不发布。不要为解决镜像网络问题删除数据库卷、覆盖 .env 或重建索引。
该路径不替代恢复网络后的正常 Dockerfile 完整构建，也不代表更换或重新验证了依赖。

### 当前中文操作路径

1. `docker compose --profile app --profile mail up --build -d --wait`；不要删除正常项目的卷或覆盖现有 `.env`。
2. 打开 http://localhost:5173，顶部“中文 / English”切换；刷新验证选择保存。
3. 打开验收报告中的已保存时间变化会话，查看 Alex、Nov 5 / Nov 8 和两次会议证据，不重复请求模型。
4. 会议页检查第二次会议已就绪、日期与时区、原文证据和未批准草稿；记忆页选全部历史查看新旧版本。
5. 邮件保持 local 和外部发送 false，仅允许本地 Mailpit 演示。
6. PPT 真实内容没有通过，当前任务失败。只能把私有六页副本用于问题审阅，不能当作验收成品。

语言保存于每次提交；重复上传不为切换语言创建重复会议或邮件。旧内容不自动翻译。
更换模型或向量维度、重建索引、清空数据、追加真实调用，都不属于本次收尾操作。

Phase 6 local delivery, 2026-11-03 (Asia/Shanghai). This is a single-user,
loopback-only demonstration. Public authentication and public deployment are not
accepted. Never expose the demo API publicly. Phase 6 was not deployed, committed
or pushed; the existing normal stack was not recreated during acceptance.

## Prerequisites and configuration

Use Python 3.13+, Node 22+, Docker Compose and the committed lockfiles. Keep the
private implementation MD/PDF and root .env outside Git. Copy .env.example to
.env only on a fresh clone; never overwrite an existing .env or its credentials.
The root file serves local backend and Compose. Existing data and vector profiles
must be preserved; do not run compose down --volumes on the normal project.

| Root .env setting | Line | Meaning |
| --- | --- | --- |
| LLM_MODEL / LLM_API_KEY / LLM_BASE_URL | 19 / 21 / 23 | Existing Gemini model/profile |
| LLM_REASONING_EFFORT | 73 | Existing minimal thinking setting; preserve it |
| EMBEDDING_API_KEY / BASE_URL / MODEL / DIMENSIONS | 38 / 40 / 43 / 44 | Existing gemini-embedding-001 / 768 profile |
| SEARCH_API_KEY / SEARCH_BASE_URL | 66 / 110 | Tavily Key (now configured locally) / official endpoint |
| SEARCH_MAX_RESULTS / TIMEOUT / CACHE_TTL | 111 / 112 / 114 | 5 / 15 seconds / 300 seconds |
| SMTP_MODE / SMTP_EXTERNAL_SEND_ENABLED | 95 / 102 | local / false; keep these values |
| SMTP_USERNAME / SMTP_PASSWORD | 69 / 70 | Optional credentials; blank for local Mailpit |
| DEMO_ALLOWED_RECIPIENTS | 71 | demo@example.test, exact test allowlist |
| PRESENTATION_MAX_OUTPUT_TOKENS / JOB_TIMEOUT / CONVERSION_TIMEOUT | 116 / 117 / 118 | 6000 / 240 seconds / 90 seconds |
| PRESENTATION_NODE / PRESENTATION_LIBREOFFICE | 120 / 121 | Local executable paths when using hybrid development |

Do not paste Keys into chat or source files. Search requires a Tavily Key, supplied
locally at line 66. Keyless search and optional-web generation must fail clearly.
Do not replace missing research with sample results. Embedding provider, model,
Base URL, dimensions and normalization identify an index; changing them requires
an explicit owner-approved reindex operation, never an automatic rebuild.

## Startup (manual, after owner approval)

The following is the reproducible startup command, not an operation performed
against the normal stack during this Phase 6 task:

```powershell
docker compose --profile app --profile mail up --build -d --wait
```

Open http://localhost:5173, API health http://localhost:8000/api/health,
API docs http://localhost:8000/docs and Mailpit http://localhost:8025. Ports bind
127.0.0.1. Preserve named Postgres, Redis and private-file volumes. Restarting or
upgrading an approved build must not delete them. Migration head remains
0006_presentations; Phase 6 adds no schema or index migration.

For local development, create .venv, install backend/requirements-dev.lock and
run `python scripts/dev.py migrate`, `python scripts/dev.py api`. In frontend,
run npm ci then npm run dev; Node/PptxGenJS renderer dependencies need a separate
npm ci in backend/renderer. LibreOffice/CJK fonts are included in containers;
native Windows conversion requires installing them and configuring line 121.
Use the existing hybrid storage/Compose setup consistently: container named
storage and host paths are different roots. Never silently mix their originals.
The full native Windows worker/storage path is still not accepted end-to-end.

## Complete demonstration: synthetic release evidence

All demo-data files are synthetic. Dates are November 2026, Asia/Shanghai, and
must remain fixed. Uploading content can send it to configured external models.
The example outline JSON is an acceptance illustration, not a production fallback.

1. Chat: send a short greeting, watch streamed output and reload. Start a new
   conversation and confirm it has separate history. If the provider fails, keep
   the failed record and error code; do not claim a generated answer.
2. Knowledge Base: upload demo-data/project_brief.pdf once. Wait for ready with
   one page and nonzero chunks. Ask who owns the API and its initial deadline;
   expect Alex and Nov 5 with a page-1 citation. Re-upload the same bytes to show
   reuse, not a fresh embedding index. A corrupt/empty PDF must show failure.
3. Meetings: upload meeting_01.txt, wait for validated extraction and inspect
   people, date/timezone, evidence, risk/task proposals and unapproved drafts.
   This exact synthetic source has an existing historical real-Gemini result;
   duplicate upload should reuse it. Do not change its title to force a new call.
4. Upload meeting_02.txt once. Inspect the Nov 4 event date, Nov 8 API deadline,
   QA authorization blocker, fixed Nov 9 demo and Alex's Nov 5 mitigation task.
   Current real validation failed twice with HTTP 503 and remains pending. Its
   failed source/job is preserved. Retry only once deliberately after provider
   availability is restored; never loop or upload renamed copies to bypass it.
5. Create a fresh chat and ask: Who owns the API and how did its deadline change?
   Expect Alex and Nov 5 → Nov 8, citing both dated meetings. Exact recall uses
   actual scoped SQL memory, not a simulated model response. With only one real
   extraction, do not claim the two-real-meeting gate passed.
6. Memory: inspect All history, event and observed times, source quotes and IDs.
   Correct a demonstration fact with a reason, then revoke that demonstration
   version and re-import. It must not reappear in recall. Preserve original
   evidence and suppression history. Only confirm an alias/merge after verifying
   the names identify the same person/project; similar names remain distinct.
7. Tasks & Actions: inspect risk-linked proposals, owners, dates and original
   evidence. Edit/save a draft to demo@example.test only. Confirm the exact saved
   revision and approve once. Inspect the actual captured Mailpit message and
   saved sent/audit state. Repeated approval/upload must not send/create again.
   External sending remains false. A timeout after acceptance requires manual
   mailbox reconciliation, never automatic resend.
8. Web: after supplying the missing Key locally and an approved configuration
   reload, search once on Presentations or use /search in Chat. Inspect actual
   source links and retrieved_at. Repeat that same query within five minutes to
   show cache reuse and the original timestamp. Model background knowledge is not
   a live search result. A quota error should stop further search calls.
9. Presentations: select the ready PDF, both ready meetings and owned memories;
   optionally enable the same web query while its cache is valid. Request exactly
   six Chinese slides. Watch retrieval/planning/rendering/conversion. Inspect
   outline/source IDs, visible source notes and full citation notes, Chinese font,
   facts and the date history on all six pages. Download PPTX and PDF; modify one
   native text shape in PowerPoint-compatible software, reopen it, and confirm
   six slides/pages remain. Real internal-plus-web generation is currently blocked
   by missing Tavily Key and unavailable Gemini, not accepted from fixture output.
10. Reload saved history/outputs. Restart persistence is exercised only on the
    isolated test stack during acceptance. Do not restart/delete normal services
    as a shortcut to fix a failed model or rebuild an index.

## Credential-independent regression

Verification sources/runners stay local and ignored under the owner's publishing
policy. Public clones do not contain these private verification files. In the
owner workspace, use:

```powershell
.venv/Scripts/python scripts/dev.py check
$env:MEMORA_TEST_FRONTEND_PORT='55273'
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:BUILDKIT_NO_CLIENT_TOKEN='1'
.venv/Scripts/python -X utf8 scripts/test_phase6.py
cd frontend
npm.cmd run check
npm.cmd run build
```

This uses memora-phase6-test with separate ports/database/volumes, independent
HTTP Providers and local Mailpit. Its downgrade-to-base/upgrade tests are
**destructive only to that disposable project**. Never point these commands at
the normal database. A skipped check is not a pass. See the A01–A22 matrix in
phase-6.md for actual results, history and blockers.

## Troubleshooting and safe recovery

- Missing Key/model: use the specific .env line above. Saving a Key does not
  change an already running container; arrange an approved recreate/reload.
- HTTP 429/503: retain request ID/status and stop the live demo. Respect server
  retry hints and finite provider retry limits; do not try model after model.
- Failed PDF: inspect error code and original format. Never mark partial work
  ready or substitute mock vectors. Index-profile mismatch needs explicit reindex
  approval, not a background repair.
- Failed presentation: inspect stage/error. Valid outlines survive conversion
  failure and are reused on explicit retries (maximum three). Interrupted/stale
  executions cannot publish or overwrite a newer attempt. No partial download.
- Preview failure: Retry preview reloads the private PDF without regenerating
  slides or calling the model. Check worker MIME type, same-origin access and
  browser console if a page does not render.
- Logs: use request_id/job_id/stage/attempt/error_code to correlate; do not log
  document text, prompts, response bodies, API headers or Keys. Application log
  events/fields are allowlisted. Keep raw Compose logs/screenshots private unless
  inspected and explicitly curated as synthetic documentation assets.
- Backups: back up Postgres and private originals together; Redis caches are not
  a replacement for evidence. Do not delete volumes or change model profiles as
  a recovery step. No normal data/index was cleared in Phase 6.

## Acceptance limits

Independent test Providers prove application behavior with real local services;
they do not prove current Gemini availability or Tavily access. Current Gemini
live recheck: 2 requests, both HTTP 503, then stopped. Embedding/Tavily/external
SMTP requests in this phase: 0. Historical real smoke passes remain historical.
Use the phase report's separate live column; do not present all A01–A22 as fully
passed with real external APIs. No commit, push or deployment is authorized here.
