# Item 9 — 澄清安全续接与正式 React（当前执行）

日期：2026-10-09。Start HEAD：`9be82b98c714e378812b8e17728c452f93951496`。C0–C2 已通过且独立审查 PASS；React U1–U3 正在实施，浏览器验收尚未完成。下方原 U0 阻塞报告按原文保留，不把历史 STOP 覆盖为 PASS。

## API / 页面消费边界

| 用户界面事实 | 服务端来源 | 当前验证 |
|---|---|---|
| 输入目标与补充信息 | GoalSpec；owned availability 决定入口可用性 | NOT RUN |
| 初始澄清、合法答复 | RunView typed clarification；窄用途同预算根 continuation POST | NOT RUN |
| 进度与失败 / unknown / cancelled | GET runs；只用用户语言呈现，不自动重派 | NOT RUN |
| 阶段安排、知识与单元 | v2_content.stages / nodes / units / guidance | NOT RUN |
| Primary / Supplement / Reference、章节及版本 | v2_content.resource_assignments[].source_snapshot | NOT RUN |
| 自己项目、阶段增量、Micro Exercise、最终成果 | v2_content.practice + guidance.practice_delta | NOT RUN |
| 别人项目源码学习 | v2_content.project_study；与自己的持续实践区分 | NOT RUN |
| 未完成课程 | typed planning issues；Compiler 拒绝时没有可确认 Draft | NOT RUN |
| Draft 编辑与确认 | 当前 Draft hash/version + decision；确认后 fresh current read | NOT RUN |
| 未来说明 / 合法顺序调整 | Item 8 context/local preview/confirm；不编辑教材或任意任务 | NOT RUN |
| 目标变化与历史 | owned semantic replan；准确 revision/lineage，不按标题继承进度 | NOT RUN |

批准 HTML 保持原样，SHA256：`dc1dd08b40520f76c1fece10858dd2c8e38843e4b2400fed0ea8b9ef2915df7b`。静态演示数据与状态切换器不进入生产 React；界面只呈现实际服务端冻结事实。

仅新 owned PG / checkpoint 和显式 Mock/Fake ports用于验证。真实产品模型、搜索、Reader 调用为 0；原正式数据库不写，公开 `/plans/generate` 继续关闭。真实产品课程质量与用户语义验收仍待另行授权。

---

## 原 U0 报告（原文保留）

# Planning V2 Item 9 — React 实施 U0 接口预检

日期：2026-10-09。结论：`ITEM9_IMPLEMENTATION_BLOCKED`。

用户已正式批准 HTML 原型。U0 发现“初始目标需要澄清后提交答案并继续”没有现成合法业务接口，触发本轮明确 STOP 边界；因此没有开始 U1 React 编码、U2 接线或 U3 浏览器验收。不是因为原型未批准，也不是因为正式生成 503 这个预期保护。

## 1. 基线、批准版本与修改范围

- Branch：`feat/n1-resource-discovery`。
- 实际 Start / Final HEAD：`9be82b98c714e378812b8e17728c452f93951496`；本轮未创建实施提交。
- 已批准原型：[planning-v2-ui.html](prototypes/planning-v2-ui.html)，SHA256 `dc1dd08b40520f76c1fece10858dd2c8e38843e4b2400fed0ea8b9ef2915df7b`；与该提交及首轮最终浏览器证据一致。原型未修改。
- 参考：[HTML 评审](ITEM9_HTML_PROTOTYPE_REVIEW.md)、[架构合同](PLANNING_V2_ARCHITECTURE_CONTRACT.md)、[Item 7](ITEM7_PLANNING_EXECUTION.md)、[Item 8](ITEM8_REPLANNING_REVISION.md)。
- 只新增本报告并在唯一 `docs/implementation/progress.md` 前置本次结果；旧 progress 字节作为完整后缀保留。正式前后端、DTO、OpenAPI、生成 TypeScript、Policy、Prompt、Schema、账本、迁移和受保护目录未修改。
- 起始 tracked tree clean，仅既有受保护未跟踪目录；900 个 tracked 文件建立哈希基线。证据保存在忽略目录 `var/planning-v2-item9-react-u0-20261009/`。

## 2. 关键阻塞：初始澄清不是可续接状态

实际调用链：

1. [V2PlanningRuntime.execute](../../backend/app/infrastructure/checkpointer/v2_planning_runtime.py) 第397–408行：Analyzer 返回非 `ready` Profile 时，直接返回 `LLMFailure("goal_clarification_required", ...)`。规范化 `goal_analysis` checkpoint 的 `save(...)` 在此失败分支之后。
2. [PlanService._execute_owned_v2](../../backend/app/application/plan_service.py) 第267–271行：Run 变为 `failed + none`，Job 变为 `failed`，不是等待用户回答。
3. [RunView / run_view](../../backend/app/api/v1/views.py) 第92–103行及 `schemas.py::RunView`：没有 typed 澄清问题或答案续接字段；错误投影只有 code/message/request_id，`details={}`。该错误当前落入通用“可重试”文案，不能据此提供重派按钮。
4. 内部 [v2_attempts.py](../../backend/app/infrastructure/providers/v2_attempts.py) 第383、523–549行仍可能在 receipt `response_payload` 保存 Provider 原始输出。因此不能声称澄清内容完全没有持久化；问题在于没有当前 UI 可读取的规范化问题及合法答案提交 / 继续合同。直接暴露原始 receipt 也不能替代该合同。

现有替代入口均不能安全完成此操作：

| 替代方式 | 实际保护 | 为什么不能代替澄清续接 |
|---|---|---|
| 再次 owned generate | `PgPlanningJobRepository.enqueue`，`job_repository.py:214–227` 检查同 actor/project 所有 V2 初始 Run，无 status 过滤；已有 failed root 也返回409 `v2_initial_run_exists`。 | 不能补答后建立第二初始 root 绕过原生命周期 / 预算。 |
| resume 失败 Run | 当前 API 没有 `/runs/{id}/resume`；`GraphRunnerPort.resume` 仅内部声明。Worker claim 只接受 queued/running Run 与合法 pending/过期 running Job，failed 不满足。 | 不能将旧 Graph 的 waiting_user 恢复嫁接到这个失败 Run。 |
| Semantic Replanning | `PgV2Revisions._base`（`v2_revisions.py:213`）要求已有合法 current V2 Plan；`submit_semantic:413` 绑定当前版本、原 root、revision context 和预算。 | 初次澄清失败没有 current Plan；这是已有计划的语义修订，不是初始失败 Run 的回答续接。 |
| 仅增加只读问题 DTO | 最多使用户看到问题。 | 没有答案写入、来源绑定和合法继续状态，仍不能继续生成。 |

这需要明确业务生命周期及保护合同，超出本轮允许的“只读展示字段投影适配”。按用户附件第四、九节要求，STOP，不制作可点击但无安全实现的继续按钮。

## 3. U0 API / DTO 消费矩阵

下表是源码和接口合同核对，未作为真实 HTTP / PG 执行 PASS。

| 用户操作 / 展示 | 已有接口、DTO 与实际限制 | U0 结果 |
|---|---|---|
| Goal 与补充信息 | `GoalSpec` 已有 target、starting_point、scope、desired_depth、outcome_purpose、constraints、project_context；`PlanGenerateRequest` 有 goal / goal_spec / prefs_snapshot。 | 可沿用字段，无需固定方向或新画像。 |
| 正常产品生成 | `POST /plans/generate` → `PlanService.submit_generation:202` 明确503。 | 预期保护，不能开放或将 UI 显示为已派发。 |
| owned 生成 | `POST /plans/v2/owned/generate` → `submit_owned_v2:216` 需 owned-only factory/jobs；正式 composition 未注入 factory。 | 只能在已有受控 owned 装配验收；不能切前端 URL 绕过正式入口。 |
| 202 / 进度 / 刷新恢复读取 | `GET /runs`、`GET /runs/{id}`；RunView 有 status、next_action、version、result_ref、error、progress。 | 有范围校验的读取，可复用；读取不代表恢复执行，不应刷新重复 POST。 |
| 澄清展示与提交答案 | RunView 无 typed questions；没有合法继续 API。 | **BLOCKED，关键 STOP。** |
| Draft 读取 / 描述编辑 / 当前 hash 确认 | `GET /plans/drafts/{id}` 与 draft decision；approve 要求当前 hash、版本和幂等键。V2 初始草案仅允许受控描述修改，身份、顺序、类型、数量变化拒绝；revision preview 不能直接 edit。 | 已有路径可复用，但本轮未实施 / 验收。 |
| current / 版本历史 | `GET /plans/current`、`GET /plans/revisions/{revision}`；无 current 或不存在的版本404。 | 已有读取；不按相同标题复制旧进度。 |
| Local Change | `/plans/v2/changes/local` 及既有 context/confirm；只允许未来说明、完整合法顺序，保护已开始/完成阶段，绑定 current/version/hash。 | 已有 current 的受控路径，不可用于初始澄清。 |
| Semantic Replanning | `/plans/v2/owned/replan`；须合法 current、同库 owned factory/jobs、原 root / 预算及版本绑定。 | 可用于已有路线，不替代初始澄清。正式装配仍不开放。 |
| cancel / unknown | `/runs/{id}/cancel` 校验 version / idempotency，终态或待核对拒绝；可能已派发时进入 reconciliation，保留 attempt。 | 不得提供“取消 unknown 后重新生成”或“重试失败澄清”。 |
| 课程事实 | PlanDraftView / PlanView 已有 `goal_spec`、`stages`、`unit_links`、`task_links`、`stage_resources`、`extensions`、`v2_content`、`v2_revision`。 | 生成 TS 已包含两项 V2 字段，内部仍是 `Record<string, unknown>`；可做展示类型适配，尚未证明 React 无损消费。 |

前端定位：`frontend/src/api/client.ts` 已有 `run/runs/cancelRun/draft/current/decide`；暂无 generate、owned replan 或历史读取方法。`api/types.ts::DTO` 可访问上述生成类型。`PlanningPage.tsx::PlanningPage` 仍为原占位页，无表单或新业务逻辑。现有导航、认证、Learning Workspace 和样式未修改。

## 4. 最小待评审范围

后续如要继续本 Goal，先单独明确“初始澄清安全续接”的最小业务合同：

- 用户能读取哪些规范化澄清问题；与原 Goal、来源、Run / root 及版本如何绑定，不直接公开内部原始 receipt。
- 答案如何在合法的新请求 / 版本中继续；保持原 root 的累计预算与幂等保护，不重派 failed / unknown，不建立第二初始 root，不改写历史 Run / receipt。
- 并发、过期答案、取消和 unknown 的拒绝规则；明确继续完成前旧状态如何保留。
- 优先现有结构承载；若必须改变冻结合同或新增 migration，先评审，不能在 React Goal 内偷改。

这只是需用户决定的合同范围，不是已选定或已实施的新工作流。正式 `/plans/generate` 的关闭不需要为解决 U0 而撤销；即使新增安全续接，后续仍应先使用 owned + Mock 完成关键闭环，再单独评审正式开放条件。

## 5. 验证、审查与剩余交付

| 项目 | 实际状态 |
|---|---|
| 已批准原型版本 / HEAD / 起始工作树 / 哈希 | PASS |
| U0 实际 API / DTO / OpenAPI / TS 定向兼容核对 | FAIL：关键澄清操作无法安全完成；已有可复用部分见矩阵。 |
| React 页面 / 组件、六状态、完整课程字段接线 | NOT RUN；U1 未开始，未复制 HTML 演示状态冒充业务。 |
| 前端测试 / build / 新 React 截图 | NOT RUN；无 React 修改，不重复执行旧原型检查替代。 |
| owned HTTP / PG / Worker / 浏览器关键业务闭环 | NOT RUN；U0 STOP 后未创建 owned 数据库、账号、Run 或 Job。 |
| 真实模型 / 搜索 / Reader / 正式产品数据库写入 | 0；正式行计数验证 NOT RUN，不虚报行数。 |
| 实施后独立审查 | NOT RUN；尚无实现。NORMAL 做真实后端调用链核对，FAST 仅前端符号 / 字段清点，未让 FAST 批准复杂行为。 |
| 文档差异 / 其余文件与旧历史保全 | PASS；仅本报告及 progress，旧 progress 原字节保留。 |

本轮请求 NORMAL `gpt-6.1-sol / medium`、FAST `gpt-6-luna / medium`；实际解析均为 NOT OBSERVABLE。主会话模型 / effort 无法通过当前工具切换或核实，未宣称切换、未改全局配置。

已批准 HTML 与其实际截图继续有效，但不是正式 React 截图。完整 Draft / incomplete / 修改预览 / current/history / 刷新重登录 / 390px React 验收、真实语义与全产品用户接受均未完成。没有可据此安全开放正式生成的结论。

最终状态：

`ITEM9_IMPLEMENTATION_BLOCKED`

`ITEM9_REACT_NOT_STARTED`

`REAL_PRODUCT_SEMANTIC_ACCEPTANCE_PENDING`

`PUBLIC_GENERATE_NOT_ENABLED`

`STOP`
