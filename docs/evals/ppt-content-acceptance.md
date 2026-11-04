# PPT 内容准确性定向修复（2026-11-04）

本轮只修改大纲证据结构、生成约束和发布校验；既有中英文界面、会议、记忆、邮件和索引保持。
没有提交、推送或远程部署。网站启动在 http://localhost:5173 ，可直接进入“演示文稿”查看最新任务。

## 结论

代码和离线回归通过，但**真实六页成品仍未通过，未发布**。最新任务：
`d8605564-21f9-4b96-9f86-3fd4fd26fa3a`，状态 failed / OUTLINE_INVALID_CITATIONS。
没有手工改写模型正文、替换引文、放宽匹配或生成假成功文件。

## 定位和修改

上轮响应第 5 页把 confirm 加强为“提交”，第 6 页增加“频繁”。原因是模型直接生成自由 bullets，整页 source_refs 不能逐条约束语气和证据。旧响应和审阅副本被复用作离线反例。

现在模型输出逐条声明，包含 kind、source_ref、quote、text。事实只能引用内部记录，正文为空，由服务端输出原样引文及记录日期；不能由模型改写成更强承诺。风险推断标为“待验证”，建议行动标为“未承诺”。每条推断/建议也必须有精确引文；不允许建议创建日期承诺，人物及日期要有对应证据。PPT 备注保存逐条分类和引文。

正常生成不再接受旧的自由 bullets 大纲；旧的已保存成品保持原样，不自动重写。无资料的概念性演示继续使用既有路径。发布前的结构、页数、引用、事实、渲染及文件所有权检查保留。模型代码不能进入固定 PptxGenJS 渲染器。

为避免把已验证的字面引用误当成模型改写，语言/语义守卫审查模型新写的文字；字面事实先接受更严格的内部原文精确匹配，引用正文不被润色或翻译。中文用于标题、分类、推断和建议，事实引文保留原语言。

## 本轮真实请求

Gemini **2 次，均 HTTP 200**（一次首次生成、一次明确缺失字段后的定向复验）；没有自动模型重试或切换。
仍为 gemini-3.1-flash-lite，reasoning_effort=minimal，max_tokens=6000。
Tavily 0、Embedding 0、外部 SMTP 0。复用两次已验证会议和五条上轮真实 Tavily 响应，保留原检索时间；没有重新提取、重建索引或刷新检索时间。
本轮 2 次与上一轮 3 次分开计数。此后只有离线回放，没有继续消耗模型额度。

首次响应遗漏 5 个 quote 必填字段，并把“Bailey 和 Casey 的具体职责未知”作为可自由改写的 fact.text。严格拒绝后，补强所有分类必须填引文、未知职责应单独作为推断的提示，进行一次定向复验。

第二次响应不再出现“提交计划”或“日期调整频繁”，但第 5 页第 2 条网页建议使用了：
`encourages contractors... to communicate`。它不是 web:1 原来源中的连续字符串，省略号改写不能充当精确证据，因此拒绝整份发布。
另外，第 6 页风险推断提到 2026-11-08，但该条自己的 quote 仅为 `QA is still blocked`，也需要补足对应日期证据；不能默默借用另一条事实的引文。

## 逐页审查范围

| 页 | 实际响应检查 |
| --- | --- |
| 1 概览 | 客户演示 Nov 9 使用原文，确认事实/推断分类可见 |
| 2 职责 | Alex 所有权引用原句；Bailey、Casey 未补造职责，分别标为推断 |
| 3 日期变更 | Nov 5、Nov 8 分别绑定两次会议引文，保留历史顺序 |
| 4 风险 | QA 阻塞为确认记录，网页方法为建议，无新指派日期 |
| 5 行动 | confirm 原句保留；网页建议的省略号引文不精确，失败 |
| 6 总结 | 风险推断的 Nov 8 缺少该条引文支持，未验收 |

真实请求在发布前失败，因此本轮**未生成真实合格 PPTX/PDF**，真实成品字体、布局、可编辑性和完整预览属于阻塞项，不能拿上轮私有审阅副本替代。
独立测试 Provider 的完整链路实际生成六页可编辑 PPTX/六页 PDF，检查中文字体、引用备注、编辑副本 LibreOffice 重新打开、下载与所有权；它只证明文件链路，不能代表真实模型内容通过。

## 实际验证

- `.venv/Scripts/python scripts/dev.py check`：Ruff、格式、mypy（55 文件）、100 单元测试通过；52 个集成用例 deselected 不计为通过。
- `.venv/Scripts/python -X utf8 scripts/test_acceptance_i18n.py`：仅选择 `tests/integration/test_phase5.py`，最终 1/1 通过。启动器旧阶段横幅不代表全套重跑。
- `scripts/dev.py export-api`、frontend `npm.cmd run api:types`、`npm.cmd run check`、`npm.cmd run build`：通过。
- 本地采用已验证依赖镜像，仅重建应用源码与固定渲染器；Compose 使用 `--no-build --wait` 更新。没有变更依赖、.env、数据库结构或索引。
- 历史中英文回归结果保持，不宣称重新执行未受影响的全部流程。模型测试适配器更新了新结构契约，不作为正常服务 fallback。

本地证据：`logs/bound-backend-final.log`、`logs/bound-integration-final.log`、`logs/bound-frontend-check.log`、`logs/bound-frontend-build.log`、`logs/bound-acceptance/`、`logs/bound-repair/`、`logs/bound-diagnostic.json`。测试/响应/脚本继续被 Git 忽略。

## 网站检查

打开 http://localhost:5173 ，可检查原有中英文切换、会议和时间变化会话。
进入“演示文稿”查看最新失败任务。它没有正式下载，不能作为已验收成品。
此前会议/跨会话通过项和 Phase 1/2 全量真实待验项保持；邮件为本地 Mailpit，外部发送关闭。
