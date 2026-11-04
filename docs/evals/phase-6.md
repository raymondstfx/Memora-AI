> 最新定向修复：逐条事实/推断/建议证据绑定已实施，100 单元测试及六页测试 Provider 链路通过；本轮真实 Gemini 2 次，仍因第 5 页省略号引文不匹配而拒绝发布。网站已启动。详情见 [PPT 内容验收](ppt-content-acceptance.md)。以下保留此前记录。

> 2026-11-04 最新修复结论：99 单元测试、累计 37 个受影响集成用例及 5 个双语浏览器用例通过；第二次真实会议与跨会话时间变化已通过。真实六页成品内容仍失败并被拒绝发布。实际 Gemini 3 次，其余外部请求 0 次。以下为历史阶段报告；本轮精确命令、逐页审阅、保留项及中文演示见 [final-acceptance.md](final-acceptance.md)。没有重跑未受影响的全套基础设施验收，没有新迁移、提交、推送或远程部署。

# Phase 6 acceptance and delivery report

**2026-11-04 follow-up:** local services now load Phase 6. Real Tavily passed;
meeting HTTP 200 still failed validation. Six-slide files passed but content
review found date/role issues. See [final acceptance](final-acceptance.md) for
current results, request counts and direct demonstration steps. The dated record
below remains historical.

2026-11-03, Asia/Shanghai. Phase 6 source work is complete with external acceptance
failures/blockers explicitly retained. This is not an all-green real-API signoff.
No commit, push or deployment was performed. Existing normal services were not
rebuilt/recreated, databases were not cleared and indexes were not rebuilt.
The owner explicitly authorized Phase 6 and a bounded live recheck. AGENTS.md,
the private specification and Phase 0–5/latest provider reports were read first.

## Results at a glance

- Independent Providers: unit/static checks pass; full local regression results
  and actual final command evidence are recorded below. The real local services
  include PostgreSQL/pgvector, Redis, RQ, Mailpit, Node, LibreOffice and PDF.js.
- Current real Gemini second-meeting extraction: **failed**, two HTTP 503
  responses (one initial request and one explicit extra attempt), then stopped.
  Application error PROVIDER_HTTP_ERROR; cause beyond the observed HTTP status
  is not inferred. No further model experiments or repeated quota consumption.
- Current real Tavily and internal-plus-web six-slide synthesis: **blocked** by
  missing SEARCH_API_KEY, root `.env:66`, plus unavailable Gemini for synthesis.
- Existing first real extraction remains ready with its original three tasks.
  Fresh SQL-based owner recall from that real result, saved citation/history and
  browser reload passed without another external request. This does not establish
  the two-real-meeting temporal gate.
- External email stays disabled. Only isolated local Mailpit is used for sends.
  Current source has not replaced the previously running normal application.

## Delivered work and defects fixed

1. Synthetic public demo set: project_brief.pdf, meeting_01.txt, meeting_02.txt,
   expected_analysis.json and presentation_outline_example.json. Dates/timezone
   match November 2026 / Asia/Shanghai. Source line expectations identify API
   owner, initial and updated deadlines. The outline illustration is not a runtime
   fallback; real sourced generation must bind retrieved source IDs.
2. Responsive loaded forms, checkbox choices, long evidence/source wrapping,
   mobile touch targets, explicit initial loading/empty/error states and preview
   progress/retry. Preview changes clear old canvases before loading another file.
   Reloading preview does not regenerate or consume model quota. Sidebar/readiness
   labels now describe actual capabilities rather than old planned phases.
3. Confirmed stale-presentation race: a worker finishing after interruption or
   retry could previously write old files/state over a newer execution. Fixed with
   attempt-bound row leases for outline/stage/final publication, callback attempt
   metadata, matching failure updates and consistent owner/row lock ordering.
   Both artifacts are atomically replaced under the valid lease before ready.
   Tests replace a lease during planning and conversion and reject old callbacks.
4. Search rejects credential/control-character result URLs and unsafe remote HTTP,
   credential-bearing, query-bearing or fragment-bearing Base URLs before sending
   credentials. Local injected test endpoints remain supported. Browser data is
   escaped; untrusted evidence never supplies executable renderer JavaScript.
5. API responses retain X-Request-ID and private/no-store plus nosniff/referrer
   headers. Nginx adds same-origin CSP, frame protection and correct module-worker
   MIME. PDF.js workers/fonts and all preview pages pass under the policy. Public
   authentication remains outside this loopback demonstration, not claimed solved.
6. Logs allowlist event names/fields and expose job_id/stage/attempt without Keys,
   prompts, documents or provider response bodies. Arbitrary formatted log text
   is redacted. Request, job and audit identifiers support troubleshooting.
7. Slide wrapping preserves ISO dates/English words. Six distinct Chinese slides
   cover overview, owners, date history, risk, action and acceptance. Every page's
   content, short source notes, CJK font and layout were inspected; citations retain
   complete source metadata in notes. The editable-text round-trip remains real.
8. Test harness race fixed: one duplicate memory probe ran immediately after API
   restart before readiness. Removed the premature duplicate; the surviving probe
   runs after health/readiness. This was a verification failure, not counted as a
   pass. Only isolated test services were restarted.

No new migration or schema change is needed; head stays 0006_presentations.
[Runbook](../runbook.md) includes safe recovery and full reproducible demo steps.

## A01–A22 acceptance matrix

PASS in the independent column means actual execution with independent test
Providers and genuine local services. It is not a real Gemini/Tavily pass. Where
an operation needs no external model (validation, scoped SQL, SMTP transport,
files), the actual local operation is identified separately.

| ID | Acceptance case | Independent/local regression | Real external API / normal-data evidence |
| --- | --- | --- | --- |
| A01 | Streaming chat and reload | PASS: streamed frames, saved/reloaded answer, cancellation and errors | Historical Gemini streaming smoke passed; current full live gate remains pending after HTTP 503 |
| A02 | Separate conversations | PASS: browser creates/switches/reloads separate conversations | Existing-real-data SQL owner conversation reload passed; not a new live LLM conversation gate |
| A03 | PDF ready/nonzero chunks | PASS: real private upload, RQ parsing/indexing and dimensions | Historical tiny real 768-dimension embedding pass retained; no new embedding call after model failure |
| A04 | PDF answer/page citation | PASS: retrieved PDF and page-1 citation, saved/reloaded | Historical Gemini RAG/page smoke retained; full live gate pending |
| A05 | Unsupported/empty PDF | PASS: visible failure/retry, no partial ready | Deterministic failure handling verified locally; no external API needed |
| A06 | First meeting extraction | PASS: schema/evidence/date/people/tasks | PASS historical real sample reused, original ready state and three tasks preserved |
| A07 | Second meeting justified risk | PASS: exact evidence, risks and proposals | FAIL: two real requests returned HTTP 503; no partial business records |
| A08 | Owner/due task rows | PASS: actual Postgres rows, timezone normalization | First real meeting rows remain correct; second real meeting blocked by A07 |
| A09 | Editable risk email draft | PASS: revision, recipients, body, evidence and task linkage | Historical first real draft stays unapproved; no normal draft silently changed |
| A10 | Approved test email delivered | PASS: actual local Mailpit acceptance and stored delivery state | Local-only acceptance; no external SMTP or external inbox claim |
| A11 | Email idempotency | PASS: repeated approval/concurrent claims produce one capture | Actual Mailpit transport under independent-extraction fixtures; external transport not attempted |
| A12 | Cross-chat owner/meeting recall | PASS: fresh conversation, tool records and citations | PASS for Alex + first real meeting via stored SQL, browser reload; two-real-meeting expansion still pending |
| A13 | Nov 5 → Nov 8 with both meetings | PASS: public fixture sources, out-of-order history and both dated citations | BLOCKED by failed second real extraction; never reported as a live pass |
| A14 | Corrected memory in later recall | PASS: real Postgres versions/correction/revocation/suppression | Normal historical facts not edited merely to force a live check |
| A15 | Web sources/retrieved_at | PASS: actual adapter contract/cache/browser metadata using independent HTTP source | BLOCKED: Tavily Key absent at .env:66; no invented live result |
| A16 | Honest web failure | PASS: missing Key, quota/provider errors, unsafe URL/config and no fake answer | PASS normal missing-Key 503 confirmed, no external request |
| A17 | Valid six-slide editable PPTX | PASS: six native-text XML slides, download, edit/reopen through LibreOffice | Real mixed-context model synthesis BLOCKED; file/renderer acceptance is real local work |
| A18 | Complete six-page PDF preview | PASS: six nonblank pages, CJK/font/content/citations, all PDF.js canvases and retry | Same file-level local acceptance; no claim of live generated content quality |
| A19 | Restart persistence | PASS: isolated Postgres/Redis/API/worker restart, IDs/values/evidence survive | Normal services not restarted/deployed by this task |
| A20 | Ownership | PASS: foreign metadata/jobs/originals/preview/download rejected | Actual API/SQL scope tests; fixed demo identity is not public authentication |
| A21 | Prompt injection boundary | PASS: malicious meeting/PDF evidence cannot approve/send mail or execute renderer code | Boundary verified locally; live-model semantic resistance is not claimed universal |
| A22 | Duplicate meeting | PASS: repeated exact source reuses meeting/job and has no duplicate tasks/mail | Existing real first source reused; failed second attempt has zero partial risks/tasks/drafts |

The full matrix is reviewed. All application/local gates are exercised; current
real A07 failure and downstream A13/A15/A17 live blockers remain open.

## Exact commands and evidence

| Command/check | Actual result |
| --- | --- |
| `.venv/Scripts/python scripts/dev.py check` | PASS: Ruff lint/format, strict mypy (54 app files), 87 unit tests |
| `cd frontend; npm.cmd run check` | PASS: Prettier, strict TypeScript and generated api:check |
| `cd frontend; npm.cmd run build` | PASS: Vite production build, lazy presentation/PDF.js chunk |
| `.venv/Scripts/python -X utf8 scripts/test_phase6.py` | PASS: 51 integration tests, 19 browser tests, real isolated migration cycle and restart persistence; logs/phase-6-final-verified.log |
| Real-provider bounded recheck | FAIL HTTP 503 twice; retries then stopped, sanitized local record |
| Existing real-data owner/browser reload | PASS: source citation/history retained, no extra model call |
| Private-file/secret/ignore scan and diff --check | PASS: no configured secrets/private spec/raw tests/runtime artifacts in public candidates; diff --check clean |

Runner environment:

```powershell
$env:MEMORA_TEST_FRONTEND_PORT='55273'
$env:PLAYWRIGHT_CHANNEL='msedge'
$env:BUILDKIT_NO_CLIENT_TOKEN='1'
.venv/Scripts/python -X utf8 scripts/test_phase6.py
```

The fixed memora-phase6-test project uses separate memora_test Postgres, Redis,
Mailpit and private volumes/ports. Upgrade/downgrade-to-base/upgrade and Alembic
drift checks run only there. Destructive cleanup is restricted to those test
volumes. No metadata.create_all workaround, normal-volume deletion or index
rebuild. Test sources/runners remain ignored under the owner's publication policy;
public documentation includes only curated synthetic fixtures/screenshots.

Earlier complete runs passed 51 integration and 19 browser tests. One subsequent
consistency run passed its 51 integration tests but hit the premature restart
probe described above; it was not counted as a full pass. The final log, logs/phase-6-final-verified.log, records 51 integration and 19
browser passes and supersedes that interrupted run. The final security unit
suite records 87 passes. Local logs are ignored.

## Actual live request record

Local sanitized evidence: logs/phase-6-live.json. Normal configured Gemini model,
Base URL, minimal reasoning and 768-dimension embedding profile were preserved.
For this bounded verification process only, automatic provider retries and schema
repairs were zero, followed by one explicit second attempt. No .env setting or
running normal service was reconfigured/deployed to achieve a pass.

| External service | Requests this phase | Result |
| --- | --- | --- |
| Gemini chat/meeting | 2 | HTTP 503, HTTP 503; error PROVIDER_HTTP_ERROR; stopped |
| Embedding | 0 | Not consumed after model failure; prior historical result retained |
| Tavily | 0 | Missing SEARCH_API_KEY, .env line 66 |
| External SMTP | 0 | Disabled throughout |

Local Mailpit traffic is separate and comes from actual local regression sends.
The first real meeting was reused without a new model call. The second source
and failed job remain inspectable. It has no partial tasks, risks, drafts or
ready memory publication. The first meeting remains ready with three tasks.
A fresh owner question uses actual SQL memory from that historical real
extraction; its complete answer/citation was reloaded through the normal browser
using GET-only interception (no hidden sends/model calls). Two-real-meeting
history and a current live search+internal deck are explicitly not accepted.

Configured credentials are present at .env lines 21 (LLM) and 38 (Embedding).
Missing Tavily credential belongs at line 66; Base URL is line 110. SMTP is local
at line 95, external sending false at 102. Existing provider/model/Base URL and
embedding dimension lines remain unchanged: 19/23/73 and 40/43/44. No Keys were
printed or put into documentation. No alternate models or accounts were tried.

## Six-page inspection and screenshots

[Curated gallery](../screenshots/phase-6/README.md) is explicitly independent-
Provider synthetic output. All six pages were rendered and visually reviewed:
overview, responsibilities, Nov 5 → Nov 8 timeline, risk, actions, acceptance.
Chinese text and source footers are present with WenQuanYi Zen Hei; full evidence
and URLs remain in notes. Text shape edit/reopen succeeds and PDF count stays six.
The contact sheet intentionally shows an edited first title. Initial date-wrap
splits were fixed and rechecked; full ISO dates now remain intact. Mobile screens
wait for loaded content and show no horizontal overflow on critical pages.

## Open gates and handoff limits

- Real second-meeting extraction: FAILED, provider HTTP 503 twice. Investigate
  provider availability using the retained request statuses before one future
  explicitly approved retry. Do not blindly loop or change models.
- Real Tavily: BLOCKED, missing Key at .env:66. Search cache cannot replace a
  missing credential or prove a new live result.
- Two-real-meeting temporal recall and real internal+web six-slide model output:
  BLOCKED by those prerequisites. Existing Phase 1/2 full live gates and broader
  model semantic quality remain pending, with historical smoke passes preserved.
- Native PowerPoint Desktop/native Windows RQ/hybrid end-to-end, external SMTP
  TLS/auth/deliverability and public authentication/deployment remain unaccepted.
  Fonts are referenced, not embedded. The loopback demo is not a production
  security signoff. No public deployment was attempted or authorized here.

Complete reproduction, manual startup and safe recovery: ../runbook.md. Stop
here; no commit, push or deployment until the owner's next explicit instruction.


## 2026-11-04 最终修复的实际验证

- 根目录 `.venv/Scripts/python scripts/dev.py check`：Ruff 检查/格式、mypy（55 个源文件）、99 单元测试通过；52 集成用例 deselected，不计通过。
- `.venv/Scripts/python scripts/dev.py export-api`，frontend `npm.cmd run api:types`、`npm.cmd run check`、`npm.cmd run build`：通过。
- `.venv/Scripts/python -X utf8 scripts/test_acceptance_i18n.py`：分次受影响集成选择累计 37 个用例，修复失败后复验；最后版本仅再选 `tests/integration/test_phase5.py`，完整六页测试 Provider 链路 1/1 通过。未重复未受影响的全套基础设施验收。
- frontend（`TEST_BASE_URL=http://127.0.0.1:55273`、`PLAYWRIGHT_CHANNEL=msedge`）`npm.cmd exec playwright test i18n.spec.ts -- --workers=1`：原隔离用例 4/4 通过；新增非 JSON 故障用例在正常服务上拦截响应后 1/1 通过，累计 5 个不同浏览器用例。
- `docker compose --profile app --profile mail up --build -d --wait --wait-timeout 180`：正常六个服务健康，迁移成功，仍为 0006_presentations，无新结构变更。
- 保存的实际响应离线回放、Poppler 六页视觉检查、原生文本独立副本 LibreOffice 重新打开：文件属性可验证，但正常任务因事实不忠实保持 failed，没有发布成品。
- 真实外部请求：Gemini 3（会议 1、大纲 2，均 HTTP 200）；Tavily / Embedding / 外部 SMTP 0；没有自动重试、换模型或重新建立索引。
- 所有原有业务行 ID、索引配置、首次会议摘要和 .env 散列保留；运行源码/镜像与最终版本一致。真实会议时间变化验收通过，真实六页内容仍失败。详见最新 [最终报告](final-acceptance.md)。

最后一次镜像更新遇到 Docker Hub 连接超时，该次完整构建不记通过。使用已有已验证的依赖镜像，仅复制最终后端源码及经 Vite 构建/密钥扫描的前端静态产物，临时镜像层构建成功；`docker compose --profile app --profile mail up -d --no-build --wait` 和前端单独更新通过。最终只读指纹/健康/数据保留检查通过。真实业务调用计数仍为 Gemini 3，其余 0。


## 2026-11-04 前端设计适配补充

递归核对全部六套 code/screen、共用 DESIGN 与产品说明；完成七个原业务页与产品概览的统一适配。
详细目录映射、改动、差异、命令及演示见 [frontend-design.md](frontend-design.md)。
`npm.cmd run check`、`npm.cmd run build` 通过；生产前端上的 `tests/design.spec.ts --workers=1`
为 8/8（0 跳过，25.1 秒），包含 48 组双语/响应式页面状态。正常服务只读截图 32 组，
无脚本异常、无整页横向溢出、0 次写接口请求。数据/配置/索引保持检查通过，六项服务健康。
本轮 Gemini、Embedding、Tavily、SMTP 实际请求均 0；没有重新验收或覆盖此前真实 PPT 内容失败，
没有修改后端业务、重建索引或清理数据；未提交、推送、远程部署。
