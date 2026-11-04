> 最新定向修复：逐条事实/推断/建议证据绑定已实施，100 单元测试及六页测试 Provider 链路通过；本轮真实 Gemini 2 次，仍因第 5 页省略号引文不匹配而拒绝发布。网站已启动。详情见 [PPT 内容验收](ppt-content-acceptance.md)。以下保留此前记录。

# 最终验收修复与中英文支持（2026-11-04）

本节是当前结论；下方保留上一次验收原文。范围为已有缺陷和国际化，没有新增业务功能。
本次未提交、推送或远程部署。正常本地服务已重新构建，原有配置、数据和向量索引保留。最终比对确认：所有原有业务行 ID、文档索引配置和首次会议摘要均未改变；`.env` 字节散列不变；运行中后端源码与工作区一致，前端使用最新构建镜像，两个健康接口均为 200，失败任务下载返回 409。

## 当前结论

| 项目 | 结果与界限 |
| --- | --- |
| 中英文界面 | 通过：默认简体中文，顶部“中文 / English”切换，localStorage 持久化；七个页面在 1280 / 390 像素宽度检查，两种语言无横向溢出 |
| 界面覆盖 | 导航、表单、按钮、状态、加载、错误、空状态、校验、确认框及无障碍标签已接入统一词典；技术标识和原始资料保持原文 |
| 新内容语言 | 聊天请求与会议上传/失败重试提交语言；会议 JSON 元数据及 PPT request_json 保存提交语言，缓存区分语言；邮件草稿按会议提交语言生成。明确的输出语言要求优先 |
| 已有内容保护 | 切换语言不翻译、不重新生成已有消息、会议、记忆、邮件和文件；重复会议仍复用原记录，不因语言变化重复写入 |
| 第二次真实会议 | 通过：一次 Gemini HTTP 200，三位人物职责均为 null，1 个风险、1 个任务、1 封未批准草稿；原文校验和、引文/行号、Nov 4 上海日期、Alex 的 Nov 5 确认计划任务均核对 |
| 两次真实会议的跨会话问答 | 通过：复用首次已成功的真实提取，新会话回答 Alex 负责 API，Nov 5 → Nov 8，引用两场会议；使用带来源的时间 SQL 检索，没有新增模型/Embedding 调用 |
| 默认五来源的预算问题 | 通过输入路径：去掉 snippet/text 重复，网址与文本去重、相关性排序，优先保留内部原文，按保守 UTF-8 字节/Token 上界裁剪网页摘要；五条实际 Tavily 来源均保留 ID、URL、原检索时间。两次真实大纲输入分别 11838 / 11925 字节，均低于 12000，均获得 HTTP 200 |
| PPT 日期/职责 | 已修复源日期/时区输入和显式职责约束。最新保存响应的 Nov 5/8/9 日期及 Alex/未知职责正确；中文紧邻 API/QA 的词边界误判已修复并回归 |
| 大纲语言字段 | 已修复：请求为 zh，但实际中文大纲自报 en。现在先检查正文语言，再以提交语言设置文件语言元数据，不修改正文，也不接受错误正文语言 |
| 真实六页内容验收 | **失败，未发布**：保存响应把“确认计划”加强为“提交计划”，并声称“日期调整频繁”。两者没有内部证据，最终离线回放必须拒绝。没有手工改写正文后宣称通过 |
| 六页文件审阅 | 仅对被拒响应生成私有取证副本：六张原生文本幻灯片、六页 PDF，Poppler 逐页渲染检查中文字体、布局及引用；另行编辑独立原生文本副本后，实际通过 LibreOffice 重新打开并转换为六页 PDF，原始副本未覆盖。它不是已验收的正常成品，正常任务保持 failed，下载不可用 |
| 邮件与索引 | 本地 Mailpit 模式；外部发送关闭。本轮没有真实 Embedding、Tavily 新搜索、外部 SMTP，也没有重建索引 |

不能把“模型 HTTP 200”“文件可以打开”或“引用 ID 有效”当作事实验收通过。
本次交付通过的部分与最后的真实 PPT 内容失败分开记录，仍需后续有界真实生成验证才能关闭成品验收。

## 根因、修复与来源要求

1. 上一次第二会议失败只保存了脱敏请求信息，原始 JSON 已丢弃，不能声称还原了确切失败字段。本次保留严格结构和事实要求，增加仅含字段路径/类型的诊断，补充 schema 提示、源语言字段和本地日期；只允许对**唯一、完全一致**的引文纠正行号。歧义、改写、虚构姓名/职责/期限仍失败。本次该会议真实提取成功。
2. 原 PPT 使用 UTC 日作为当地会议日期。现在传入原文行号、local_date、timezone、date_precision、明确/未知职责和字面所有权声明。Nov 2 Asia/Shanghai 不能变成 Nov 1；未知开始时间不被编造。
3. 网页只提供一般建议，不能建立项目负责人或截止日期。内部事实不为网页腾预算而截断；保护的内部资料本身过大时，调用模型前明确失败。网页摘录裁剪不改写源链接、检索时间或引用 ID。保守字节上界不是服务商的精确计费 Token 数。
4. 规划结果检查日期、已知人物职责、引文来源，以及本次发现的承诺加强和无来源频率陈述。明确的网页检索日期只能作为来源元数据，不能借此证明项目日期。明确“负责人未知”与真正的职责断言分开校验。
5. 语言词典不调用翻译 API。模型仍可能输出不忠实文字；确定性守卫覆盖已知问题，不能证明任意自然语言陈述都被证据蕴含，最终内容仍需要逐页审阅。

## 本轮真实外部请求计数

| 请求 | 服务 | 次数 | 结果 |
| --- | --- | --- | --- |
| 第二次会议提取 | Gemini | 1 | HTTP 200，严格校验后原子入库 |
| 五网页来源 + 内部会议/记忆的大纲 | Gemini | 1 | HTTP 200；触发事实校验，未发布；这次没有保存原始正文，不能断言其确切失败条目 |
| 收紧职责/来源提示后的大纲 | Gemini | 1 | HTTP 200；保存了脱敏返回。初始发现语言字段不一致；最终离线验证继续拒绝不忠实承诺 |
| Tavily 新请求 | Tavily | 0 | 复用上次五条真实响应，**不是本轮实时搜索**，保留原 retrieved_at |
| 向量请求 / 重建 | Embedding | 0 | 配置及已有索引保持不变 |
| 外部邮件 | SMTP | 0 | 外部发送仍关闭 |

**合计 Gemini 3、Tavily 0、Embedding 0、外部 SMTP 0。** 自动模型重试为 0；没有自动切换模型。
参数仍为 gemini-3.1-flash-lite / reasoning_effort=minimal；会议 max_tokens=3000，大纲=6000。
脚本导入路径和临时目录权限曾在 HTTP 传输前阻止执行，已修复，额外外部请求为 0。
最终复验只回放已保存的实际响应，不再请求模型；没有修改响应中的正文。

Tavily 来源原检索时间仍为 **2026-11-03T16:10:15.347276Z**（Nov 4 00:10:15 Asia/Shanghai）。
上次独立实时搜索已通过，本次复用不刷新这个时间。

## 实际检查与结果

本地测试/验证脚本按既有发布政策被 Git 忽略，只在所有者工作区保留。

| 实际命令/范围 | 结果 |
| --- | --- |
| `.venv/Scripts/python scripts/dev.py check` | Ruff 检查和格式、mypy 55 文件、**99 单元测试通过**；本轮未执行的 52 个集成测试被 deselect，不计为通过 |
| `python scripts/dev.py export-api`；frontend `npm.cmd run api:types` / `npm.cmd run check` / `npm.cmd run build` | OpenAPI 类型一致，Prettier、严格 TypeScript 和 Vite 正式构建通过 |
| 隔离 pytest：test_chat、test_meetings、test_memories、test_phase5、test_presentation_failures、test_phase6、test_demo_path | 累计覆盖 37 个受影响用例。英文格式旧夹具已显式指定 en；合成大纲不再假称不存在的 Nov 2 会议。失败修复后分别复验；最终新代码的六页完整链路又单独 1/1 通过。没有重跑未受影响的整套基础设施测试 |
| `npm.cmd exec playwright test i18n.spec.ts -- --workers=1` | **隔离 4/4＋非 JSON 错误 1/1 通过（5 个不同用例）**：七页面双语与窄屏、选择持久化、原消息不变、输入不丢失、提交语言/显式选择、错误切换、中文确认框、枚举值不被翻译 |
| `docker compose --profile app --profile mail up --build -d --wait --wait-timeout 180` | 先前完整构建通过；最后一次 Docker Hub 元信息请求超时，未记为通过。随后使用已验证的本地依赖镜像重建源码层/最终静态资源，`up --no-build --wait` 成功。正常六个服务健康；迁移成功，仍为 0006_presentations |
| 保存实际响应的离线回放 | 语言元数据映射通过；事实校验拒绝“不忠实承诺”，任务仍 failed，没有发布半成品 |
| Poppler + PPTX XML/字体/来源检查 | 审阅副本六页非空、原生可编辑文本、中文字体、引用/备注和布局可检查；**不计为真实成品内容验收通过** |

局部集成启动器沿用旧阶段启动横幅；横幅不代表本轮重跑了 A01–A22 全套。
本轮仅以上表实际选择的 pytest/Playwright 结果计数。历史未受影响结果继续保留。

本地证据：`logs/i18n-backend-verified.log`、`logs/i18n-browser-verified.log`、
`logs/i18n-ppt-verified-integration.log`、`logs/i18n-browser-errors-verified.log`、`logs/i18n-preservation-final.json`、`logs/i18n-ui/`、`logs/i18n-verification/`、`logs/i18n-review/`。
后两者是私有脱敏响应/审阅副本，不发布到 Git，也不应作为正式成品分发。

## 当前 A01–A22 修订

本轮新增真实证据关闭 A06/A07/A08（第二会议）、A09（草稿生成）、A12/A13（跨会话归属与时间变化）的对应待验项。
A17 的真实内容验收仍失败，A18 的新正式预览因此阻塞；私有取证预览不替代它们。
A15 保留上一次真实搜索通过与原检索时间，本轮没有新的实时搜索验收。
其他矩阵行保留此前有来源的历史结果，不声称本轮全部复测。旧报告中的 Phase 1/2 全量真实待验项继续保留。

本轮实际使用的本地命令（测试脚本按既有政策仅留所有者工作区）：

```powershell
.venv/Scripts/python scripts/dev.py check
.venv/Scripts/python scripts/dev.py export-api
.venv/Scripts/python -X utf8 scripts/test_acceptance_i18n.py
# 当前最终版本的 targeted runner 只选择 tests/integration/test_phase5.py；
# 早期 37 项选择及各失败修复结果保存在本轮分次日志中，不据启动横幅推断全套通过。
cd frontend
npm.cmd run api:types
npm.cmd run check
npm.cmd run build
$env:TEST_BASE_URL='http://127.0.0.1:55273'
$env:PLAYWRIGHT_CHANNEL='msedge'
npm.cmd exec playwright test i18n.spec.ts -- --workers=1
# 新增的非 JSON 错误用例在正常服务上拦截响应，未向后端发送聊天：
$env:TEST_BASE_URL='http://127.0.0.1:5173'
npm.cmd exec playwright test i18n.spec.ts -- --workers=1 --grep 'proxy and streaming'
```

真实验证脚本只在本次授权下执行，不应作为普通回归自动运行；本轮已停止追加真实调用。
正常服务的只读截图也已检查，阻止了所有非 GET API 操作，未产生模型调用。

## 六页审阅记录

| 页 | 核对结果 |
| --- | --- |
| 1 概览 | 日期 Nov 9 与内部决策一致；两次会议来源；中文字体/布局无缺字、裁剪 |
| 2 明确归属 | Alex 的 API 归属引用首次明确声明；Bailey / Casey 显示职责未知；无假设 QA/演示负责人 |
| 3 日期变化 | Nov 5 → Nov 8、客户演示 Nov 9、Nov 5 确认计划均有内部证据；两次会议引用；ISO 日期未断裂 |
| 4 风险 | QA 数据授权阻塞来自第二次会议，网页建议单独标示；部分接口依赖措辞仍需谨慎审阅；列布局与来源正常 |
| 5 行动 | **失败**：原文是 confirm，返回写成“提交”。日期虽正确，承诺含义不一致；不能通过 |
| 6 总结 | **失败**：“频繁”缺少证据，不能从一次期限变化推出；不能通过 |

旧成品 13788d33-5e1e-49b1-809e-b5458219c519 保留原样，不能作为修复后成品验收。
新任务 bab63dbe-5469-407e-8b07-e2fff974456a 维持失败，没有正式 PPTX/PDF 下载。
不通过删除失败记录或手工修改成品来改变结果。

## 中文演示步骤（避免额外消耗）

1. 打开 <http://localhost:5173>，顶部选择“中文”。切换 English 再刷新，确认选择保存；已有内容保持原文。
2. 打开已保存的新会话：<http://localhost:5173/?conversation=3318a23d-1a18-45ac-92c4-76ad8bd85192>。可直接查看 Alex、Nov 5 → Nov 8 和两场会议引用，不需要再次调用模型。
3. 在“会议”选择首次记录和 `Release readiness checkpoint`。第二次会议应为“已就绪”，核对原文第 5–8 行、Nov 4 上海日期、任务与未批准草稿。
4. 在“记忆”选择“全部历史”，筛选 API，查看 Nov 5 的历史版本、Nov 8 的当前版本及各自来源。查看操作不改变记忆。
5. 在“任务与行动”检查确认计划任务和中文草稿；保存/切换语言不发送邮件。外部发送保持关闭；如需邮件演示，只使用本地 Mailpit 和允许的 `.test` 收件人。
6. 在“演示文稿”查看新任务的失败状态和明确错误。**不要把旧问题文件当作已修复成品；本轮不再点击生成/重试追加真实额度。** 取证六页副本仅供本地审阅，不能充当成功演示。

## 配置、保留项与剩余问题

本次没有增加 Key 或改写 `.env`。现有位置仍是：LLM model/key/Base URL 第 19/21/23 行；
Embedding key/model/dimensions 第 38/43/44 行（gemini-embedding-001 / 768）；
Tavily Key 第 66 行；SMTP_MODE 第 95 行、SMTP_EXTERNAL_SEND_ENABLED 第 102 行。
公开 `.env.example` 仍使用空凭证占位。语言是提交参数，不需要新的全局环境变量。

- **失败**：真实六页成品的内容忠实度，需要后续经批准的有界验证才能关闭。
- **未新增复验**：新的实时 Tavily 请求、真实 PDF/RAG 全量验收、真实普通聊天英文生成；沿用已有记录，不能把响应回放或 SQL 回答当作这些真实调用验收。
- 既有 Phase 1 / Phase 2 全量真实验收待验证项保持；测试 Provider 和本地 Mailpit 结果不代表外部服务验收。
- 最终临时更新说明：Docker Hub 连接超时，后端只替换当前已测试源码，前端只替换已通过 Vite 构建和密钥扫描的静态产物；没有更换依赖。`logs/i18n-cached-source-build.log` / `logs/i18n-cached-frontend-build.log` 与 `logs/i18n-services-cached-verified.log` 保留实际结果。完整在线镜像构建需要恢复注册表连接，但当前服务已经完成更新，可直接演示。
- 没有数据库结构变更：语言保存于现有 JSON 字段，故没有新迁移或正常数据库降级操作。既有索引模型/维度标识必须继续配套，不能擅自重建。
- 不具备公开部署身份认证；继续仅用于本地单用户演示，不在本次范围扩展功能。

---

## 上一次验收原文（历史，不代表当前状态）

# Final local acceptance follow-up

Date: 2026-11-04, Asia/Shanghai. No new features, commit or push. The owner
explicitly authorized rebuilding/updating local running services; this is not a
remote/public deployment. This report supersedes the current-status portions of
the November 3 Phase 6 report while preserving that historical evidence.

## Current outcome

| Item | Result |
| --- | --- |
| Local Phase 6 rebuild/update | PASS: API/frontend/worker loaded the current source; all six services healthy |
| Existing configuration/data/index preservation | PASS: .env SHA-256 unchanged, old document profile/dimension tuples unchanged, no old table count decreased, schema remains 0006_presentations |
| Gemini 503 availability recheck | HTTP 200 on the one meeting request; 503 was not observed this time |
| Second real meeting extraction | FAIL: MEETING_INVALID_ANALYSIS (schema or quoted-evidence validation); no successful/partial business publication |
| Two-real-meeting temporal answer | BLOCKED by the second extraction; no invented Nov 8 history was inserted |
| Independent real Tavily search | PASS: one basic request, five actual sources with UTC retrieval times; same-query cache repeat made no second external request |
| Six-slide mixed-source file generation | PASS: real Gemini outline + existing first real-extracted meeting + one selected actual Tavily result; six Chinese editable slides and six PDF pages |
| Generated content quality | FAIL: the page-1 date uses UTC day Nov 1 instead of local meeting day Nov 2; some page-2 roles exceed explicit source evidence |
| Six-page file/preview checks | PASS: all pages nonblank, native editable text, CJK fonts, validated source refs/notes, browser renders all six canvases; edited copy reopens through LibreOffice |
| Mail | Local mode retained, external send disabled; no SMTP send in this follow-up |

This is not an all-green final semantic signoff. Valid files and source IDs do
not prove every generated claim is faithful. The original generated files remain
unchanged/inspectable; no silent text correction or model retry was used to make
the quality review appear successful.

## Exact real external request count (this follow-up only)

| Purpose | Service | Requests | HTTP | Parameters/outcome |
| --- | --- | --- | --- | --- |
| Second meeting recheck | Gemini | 1 | 200 | gemini-3.1-flash-lite, stream=true, reasoning_effort=minimal, max_tokens=3000; 5954 input message bytes; application rejected structure/evidence |
| Independent source search | Tavily | 1 | 200 | basic, max_results=5, include_answer=false, include_raw_content=false |
| Six-slide outline | Gemini | 1 | 200 | same model/thinking, stream=true, max_tokens=6000; valid zh outline with six slides |
| Embedding | Existing profile | 0 | — | No PDF re-ingestion, vector mixing or reindex |
| External SMTP | Disabled | 0 | — | No send |

**Totals: Gemini 2, Tavily 1, Embedding 0, external SMTP 0.** Automatic Gemini
retries and schema repairs were zero in the bounded verifier only; root .env and
running-service settings were not changed. No model list/discovery or automatic
model/account switching. The previous November 3 two HTTP 503 attempts remain
historical; they are not silently merged into this follow-up count.

The meeting HTTP 200 confirms only this attempt's availability. The existing
adapter uses schema instructions over streamed text, not a separate forced JSON
response_format. max_tokens/reasoning/model/Base URL were checked; unsupported
reasoning_effort=none was not used. MEETING_INVALID_ANALYSIS intentionally hides
raw document/model output. The discarded response does not establish which exact
schema field or quote failed; no root cause is guessed and no extra call was
spent merely to recover it. Provider availability and extraction validity are
separate statuses.

## Independent search evidence

Query: software project schedule risk mitigation testing dependencies.
Retrieved at 2026-11-03 16:10:15 UTC = **2026-11-04 00:10:15 Asia/Shanghai**.
The date/time is the actual search response receipt, not a claim that each page
was newly published or freshly fetched. A repeat within the application cache
retained the original timestamp. The selected first source page was independently
opened and its title/content matched the returned result.

| # | Actual source link | Original retrieved_at |
| --- | --- | --- |
| 1 | [Risk Mitigation in Project Management - Schedule Discrepancies](https://www.ascertra.com/blog/risk-mitigation-in-project-management) | 2026-11-03T16:10:15.347276Z |
| 2 | [The Importance of Risk Management During Software Testing](https://www.testmonitor.com/academy-articles/the-importance-of-risk-management-during-software-testing) | 2026-11-03T16:10:15.347276Z |
| 3 | [Project Risk Management Software · Riskonnect](https://riskonnect.com/project-risk-management-software) | 2026-11-03T16:10:15.347276Z |
| 4 | [Project dependencies | Atlassian](https://www.atlassian.com/agile/project-management/project-management-dependencies) | 2026-11-03T16:10:15.347276Z |
| 5 | [Dependency Risk Analysis: Definition, Examples & Uses](https://www.launchnotes.com/glossary/dependency-risk-analysis-in-product-management-and-operations) | 2026-11-03T16:10:15.347276Z |

The search is not blocked by Gemini meeting failure. Tavily Key is now configured
locally at .env line 66; SEARCH_BASE_URL remains line 110. No Key is in this report.
The public example file still contains blank credential placeholders.

## Generation scope and limits

The first mixed generation attempt used the five saved search results with the
existing first meeting. It failed **before any model request** with
PRESENTATION_CONTEXT_TOO_LARGE under the existing conservative context guard.
That failure and job history were retained.

For one bounded file-level acceptance, the verifier explicitly selected one actual
source from the already successful search response and reused its original
retrieval time. No new search request, changed global settings, fabricated result
or test Provider was involved. The normal PresentationService/Gemini renderer and
private artifact publication paths generated the result; the failed second
meeting and a new PDF were not included. This is a controlled service-level
single-source replay, not proof that default five-result UI generation fits the
current context budget. Global SEARCH_MAX_RESULTS=5 and context configuration
remain unchanged.

Presentation: 13788d33-5e1e-49b1-809e-b5458219c519

- [Existing editable PPTX](http://localhost:8000/api/presentations/13788d33-5e1e-49b1-809e-b5458219c519/download)
- [Existing PDF preview](http://localhost:8000/api/presentations/13788d33-5e1e-49b1-809e-b5458219c519/preview)

Both URLs are loopback, owner-scoped routes in the local demo. Opening existing
outputs does not regenerate or call a model. A copied native text shape was
edited, then actually reopened/converted by LibreOffice; both PDFs still contain
six pages. The original stored artifacts were not overwritten by the edit test.

### All six pages inspected

| Page | Content/layout review |
| --- | --- |
| 1 Overview | Readable Chinese, correct source footnote; **date is wrong for local meeting timezone**: shown 2026-11-01, should be 2026-11-02 Asia/Shanghai |
| 2 Responsibilities | Readable native text; Alex API plan is supported, but Bailey/Casey role labels require source confirmation rather than being treated as explicit facts |
| 3 Dates | API and plan dates Nov 5, customer demo Nov 9 match the available first-meeting evidence; no false claim that second extraction established Nov 8 |
| 4 Risks | QA authorization blocker is supported; interface/schedule discussion cites internal evidence plus actual external advice; distinguish advice/inference from recorded commitments |
| 5 Actions | API-plan confirmation Nov 5 is supported; broader coordination actions are recommendations, not newly approved tasks or email authorization |
| 6 Summary | Readable Chinese with source references; retains the fixed Nov 9 demo and does not claim a completed second-meeting history |

CJK font: WenQuanYi Zen Hei. Native slide XML text, six-slide count, source keys,
full source URLs/retrieval times in speaker notes, PDF page count and all browser
preview canvases passed. Private local inspection artifacts are under
logs/final-artifacts, including the contact sheet, original downloads, edited
copy and actual updated-service browser screenshot. These are not staged/public
customer-data screenshots.

## Local update and targeted checks

Executed the README startup/update command:

```powershell
docker compose --profile app --profile mail up --build -d --wait
```

The pre-update work queue was empty. A private preservation snapshot was taken
before rebuilding. Existing Postgres/Redis/private volumes and root configuration
were retained. Current migration head remains 0006_presentations; no normal
volume deletion, downgrade or index rebuild. Post-update /api/health, service
health, JavaScript worker MIME, actual Phase 6 browser banner and all six preview
canvases passed. The source was not committed/pushed or deployed remotely.

No unaffected full test suite was rerun. Prior 87 unit / 51 integration / 19
browser passes remain the Phase 6 regression baseline. This follow-up ran the
local rebuild (including frontend production build), preservation/health checks,
bounded live calls, actual file/XML/PDF/LibreOffice checks and GET-only browser
preview verification. Sanitized local counters/parameters are in
logs/final-acceptance.json; full prompts, Keys and model response bodies were
not logged.

## Direct demonstration steps now

1. Open http://localhost:5173 and confirm the Phase 6 banner and healthy dependency
   panel. Existing history/data are available; do not clear the database.
2. Meetings: inspect the already successful first meeting and the failed second
   meeting. The second error is now MEETING_INVALID_ANALYSIS after HTTP 200,
   rather than the earlier HTTP 503. Do not repeatedly click retry.
3. Chat: ask Who owns the API? to demonstrate actual stored-owner evidence. Do not
   claim two-real-meeting Nov 5 → Nov 8 acceptance until the second extraction is
   fixed and verified. Existing independent-Provider history tests are separate.
4. Presentations: select **项目交付与风险简报 · ready**. View all six pages and open
   Structured outline and sources. The saved source link/retrieval time is real.
   Review the page-1 timezone error and page-2 role assumptions before using it.
5. Download the existing PPTX/PDF using the links above. Correct page 1 to local
   meeting date 2026-11-02 and confirm role wording manually in your own editable
   copy. Do not present the unchanged model output as fact-checked.
6. Search UI is available with the configured Tavily Key. The query above will
   reuse the application cache only while its TTL remains valid; a new search
   after expiry is a new paid/quota-counted request. Inspecting the saved deck
   notes or this report's links requires no new Tavily request.
7. Default five-source regeneration may hit the current context limit. This
   follow-up did not change config or add a source-selection feature. A future
   explicitly approved configuration reduction (SEARCH_MAX_RESULTS at line 111)
   or a separate context-planning fix is needed for repeatable fresh generation;
   neither is silently claimed completed here.
8. Mailpit remains http://localhost:8025, SMTP_MODE=local at line 95 and external
   sending=false at line 102. No external send, no automatic task/mail side effect.

Remaining failures: meeting structured/evidence validity, real two-meeting temporal
gate, generated date/role semantic quality, default multi-source context capacity.
Existing full Phase 1/2 live gates and native PowerPoint/Windows/public deployment
limits remain as recorded. Stop here: no more live retries, commit or push.
