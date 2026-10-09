# Planning V2 Item 9 — 初始澄清续接与正式 React 验收

日期：2026-10-09。C0–C2 与 U1–U3 已完成。保留原 U0 失败报告原文；以下结果不改写历史 STOP，也不代表真实产品模型或教学质量验收。

## 基线、阶段与最终身份

- Branch：`feat/n1-resource-discovery`。Start HEAD：`9be82b98c714e378812b8e17728c452f93951496`。
- C0–C2 提交：`d142cde1c5e33b50955770b2fa4b69650c1f8a2e`，`fix(planning): support bounded initial clarification continuation`；本地 annotated `checkpoint-item9-clarification-20261009`。
- React 源码 / 截图 / 测试以本报告同批本地提交冻结；最终交付 HEAD 使用 annotated 本地引用 `checkpoint-item9-final-20261009` 精确定位，实际 SHA 随最终 Git 回执记录在 `var/planning-v2-item9-clarification-20261009/final-receipt.json` 及用户交付消息中。避免在提交内容中填写尚不存在的自身 SHA。
- 批准 HTML SHA256：`dc1dd08b40520f76c1fece10858dd2c8e38843e4b2400fed0ea8b9ef2915df7b`，保持原样。架构合同、Policy、Seed、迁移、正式环境配置和历史账本未修改。

## 真实 API 与页面消费矩阵

| 用户内容 / 操作 | 实际消费来源及保护 | 验证 |
|---|---|---|
| 目标、可选补充、入口 | GoalSpec；GET `/plans/v2/availability`，服务端 owned runtime / jobs / actor 准入决定可用性 | owned 浏览器 PASS；正常不可用分支拦截 PASS |
| 初始问题、答复、恢复 | RunView typed `clarification`；POST `/plans/v2/owned/clarifications` 绑定 parent/version/question/member/actor/project；GET 跟随 continuation | 真实 PG / Worker / Cookie-CSRF 浏览器 PASS |
| 进度、取消、失败、待核对 | GET runs/run、原 cancel API、固定 typed planning_issues；使用用户语言，不显示内部 Run/Receipt/hash/Policy ID | 真实 incomplete PASS；取消/unknown PG 合同 PASS；前端拦截 PASS |
| 目标起点、已有声明与硬约束 | `goal_spec` 或冻结 `v2_content.profile`；`serverGoal` 保留 target 来源的规范化 learner_claims / hard_constraints；不重新分析 raw goal | 实际 null goal_spec 读回 PASS；target-only 反例 PASS |
| 需要学习与已有能力 | `v2_content.capabilities.capabilities` 的 disposition、importance/learning_requirement、project_usage、learning_outcomes[].text | 公开 DTO SSR / 浏览器 PASS；Python 已有能力不变新任务 |
| 阶段安排、知识、学习单元 | `v2_content.stages[].guidance`、`knowledge[]`、`units[]`；真实公开投影不是内部 nodes/guidance 数组 | SSR / 展开 / 390px PASS |
| Primary / Supplement / Reference | `v2_content.materials[].source_snapshot`：阅读范围、section_refs、版本、限制和安全 HTTP(S) 链接 | 真实 Primary 浏览器 PASS；S/R 显示合成 SSR PASS |
| 自己项目、增量、Micro Exercise、最终成果 | `practice.carrier/tasks/final_artifact` 与阶段 guidance.practice_delta；MCP 项目使用 excluded 仍可独立小练习 | owned 浏览器 / SSR PASS |
| 别人项目源码学习 | `project_study[].requirement/case` 与阶段 project_study_refs；whole_core/slices、正常/失败、输入输出、取舍、产物、避读范围分别呈现 | 合成显示 fixture SSR PASS；真实审核案例浏览器 NOT RUN |
| 不完整课程 | Compiler 完整校验后固定 typed issues，无 Draft，无确认按钮 | 真实 owned Worker / 浏览器 PASS |
| Draft 描述编辑与采用 | 只编辑既有阶段说明；fresh Draft hash/version；显式勾选确认；成功后 fresh current | 真实 owned 草案编辑 / 确认 PASS |
| 未来阶段调整 | Item8 context、protected、local preview、confirm/cancel；不修改任务、教材或课程结构 | 真实 preview / 双刷新 / confirm v2 / cancel PASS；合法顺序 Domain/PG 合同 PASS |
| 目标变化 | owned semantic replan 202 → Run → Draft → V2 revision confirm，保留原补充事实及预算根 | 真实预算拒绝分支 PASS；成功确认前端拦截 PASS + C2 PG 成功合同 PASS；真实浏览器成功确认 NOT RUN |
| current/history | server revision / lineage；查看历史时隐藏新 Draft 编辑、预览与确认，不依据标题继承记录 | 真实 PG / 刷新 / 重新登录 / 历史隔离 PASS |

## 实现与独立审查

正式 React 复用 StudyPlan 导航、认证、工作区、浅色样式。目标输入与可选补充弹窗、typed 澄清、阶段/单元折叠、教材弹窗、教学指导、项目实践、最终成果、草案确认与 Item8 修改全部消费服务器事实，没有原型状态切换器或静态假课程进入产品。所有阶段默认折叠，遵循用户正式 React 指令第184行。既有 Learning Assistant、Summary、Prompt、Practice、Outcome 页面未重构。

后端独审四组缺陷及关闭证据详见 [澄清续接报告](ITEM9_CLARIFICATION_CONTINUATION.md)：context presence / durable binding、actor availability、答案指纹、可信 incomplete 与持久化中断。

U1–U3 独立审查最终结论 **PASS**，无未关闭 P1/P2 源码问题；源码、分层日志和桌面/手机截图均由独立审查者实际读回。独立 UI 审查主动发现并关闭：内部字段与公开 projection 混淆、未知 POST 换身份/刷新解锁、POST 与后续 GET 失败误混、preview 丢失/排序恢复、history 页面确认隐藏新 Draft、已知能力与 Micro Exercise 文案、空初始表单覆盖 Draft、规范化能力/约束字段遗漏，以及 null goal_spec / target-only 声明约束在重新规划时丢失。修复未放宽后端合同，复用同一审查者与证据包定向闭合。

未知 POST 前冻结操作种类、请求体与幂等身份，并限定 actor/project；status0、5xx 或成功状态但不可解析响应保守待核对，刷新/重新登录或 generic GET 不自动清除，不换身份重派。已明确收到 POST 响应后保存句柄，随后 GET 失败不会错误永久锁定。仍没有自动或用户自助解除 unknown 的功能；需要服务端或人工核对后续处理，页面保持禁止再次写入。

请求模型/effort：backend 与独审 Sol6.1 xhigh、前端实现 Sol6.1 medium、机械清单 Luna medium；实际模型解析 `NOT OBSERVABLE`，不把角色或提示词当作身份，不修改全局配置。

## 实际执行与证据分层

| 验证层 | 结果 | 实际证据 / 限制 |
|---|---|---|
| Backend 定向 unit/contract | PASS，119 | `unit-contract-final-green.txt`，exit0；无完整历史矩阵重跑 |
| 新 owned PG / Worker / HTTP | PASS | 31项基础矩阵 + 4/9/3定向关闭；共38个新 PG case，不把重跑子集相加；actual TCP Cookie-CSRF 完整链见 `socket-http-success.json` |
| 前端 Node / 公开 DTO SSR | PASS | `frontend-final-unit.txt`；最终项目数以日志为准；SSR 是机械字段保全，合成扩展不证明教材 reviewed |
| TS / Vite build | PASS | `frontend-final-build.txt`，72 modules，exit0；普通沙箱 realpath EPERM 保留，由受控执行完成 |
| 拦截 HTTP Edge | PASS | `frontend-final-boundary.txt`：8个不可用/终态/unknown/409场景，history 确认隔离，semantic 正分支；不接 PG / Worker / Provider |
| 真实 Edge → Vite → HTTP → 新 PG → Worker | PASS，有已记录负分支 | `react-browser-main-partial.json` 的澄清→Draft→采用v1→local preview双刷新→history→采用v2；`react-browser-resume.json` PASS：重新登录、取消preview、incomplete和history；`react-ready-selector-red.json` 中普通ready/Draft编辑/采用已执行；`react-final-readback.json` PASS：读取冻结补充事实及真实同预算拒绝 |
| Fresh owned PG readback | PASS | `browser-pg-readback.json`；10 Run / 10 Job / 5 Draft / 4 Revision 属本轮独立合成库；3个 continuation 的 parent=root，不代表正式库行计数 |
| 桌面 / 手机视觉 | PASS | 1440×1000 / 390×844；根代理与独审实际看图，保留初始、补充、进度、澄清、课程、展开、教材、未完成、preview、current/history图 |
| Ruff / import / collection / diff | PASS | 后端阶段定向证据复用；最终 git diff --check / staged check；无无关全量回归 |
| 真实收费 Provider / 搜索 / Reader、真实教材教学质量、正式 DB、整产品 E2E | NOT RUN | 产品调用0、正式写入0；全部外部端口明确 Mock；没有用 Fake / PG / UI 代替真实语义验收 |

本地证据目录：`var/planning-v2-item9-clarification-20261009/`，凭据和认证头不写入日志。owned 业务库 `studyplan_test_item9_browser_629ebe84` 与 checkpoint 库 `studyplan_test_item9_browsercp_ad53c626` 保留；无新角色，无新 migration，应用既有0025。其余每次 PG 测试的新 owned 数据库 receipts 同目录保留。

真实浏览器负结果全部保留：一次 selector 精确匹配 FAIL（未派发）；一次合成端口只识别“教材必须免费”而输入“教程必须免费”，停在 curriculum_constraints_pending，无 Draft，原 failed Run 保留，不重派；主脚本把同预算搜索耗尽误预期为成功草案而等待超时 FAIL，随后定向确认 budget/incomplete 与旧 current 保留，不放宽预算。第一次 semantic 探查发生在 profile fallback 修复前，补充事实丢失已由实际源码修复/target-only反例/正分支拦截及 fresh owned 读回关闭。最新独立 ready 用户首次 semantic 202 的冻结事实正确保留，同预算搜索限额4中初始已使用3，仍拒绝不足资料的完整草案。正式语义成功浏览器确认明确 NOT RUN。另有预填 textarea 精确 label selector FAIL，仅修正测试定位后定向读回 PASS；不重做 initial root。完整原日志不删除、不把 NOT RUN 标 PASS。

## 视觉证据与改动文件

- [首页桌面](screenshots/item9-react/01-initial-desktop.png)、[可选信息](screenshots/item9-react/02-supplement-desktop.png)、[首页手机](screenshots/item9-react/03-initial-mobile.png)、[首次澄清](screenshots/item9-react/05-clarification-desktop.png)。
- [最终课程草案](screenshots/item9-react/19-final-draft-top-desktop.png)、[展开阶段](screenshots/item9-react/20-final-draft-stage-desktop.png)、[手机展开](screenshots/item9-react/21-final-draft-stage-mobile.png)、[教材弹窗](screenshots/item9-react/08-material-dialog-desktop.png)。
- [局部修改预览](screenshots/item9-react/11-local-preview-desktop.png)、[历史路线](screenshots/item9-react/16-history-top-desktop.png)、[手机历史](screenshots/item9-react/18-history-mobile.png)、[手机不完整课程](screenshots/item9-react/15-incomplete-mobile.png)、[冻结补充保留](screenshots/item9-react/22-final-replan-preserved-supplement.png)、[最终预算拒绝](screenshots/item9-react/23-final-semantic-budget-boundary.png)。

React 改动：`frontend/src/features/planning/{PlanningPage,Curriculum,PlanningDialog,facts,planning.css}`、`frontend/src/api/client.ts`、`frontend/src/main.tsx`。受影响测试：`planning-facts.test.mjs`、`planning-render.test.mjs`、`planning-public-draft.fixture.json`（真实合成 HTTP DTO 副本，无认证信息）、`planning-placeholder.browser.cjs`、`planning-history.browser.cjs`、`planning-semantic.browser.cjs` 与 `frontend/package.json` 定向脚本。本批另更新两个 Item9 报告与唯一 progress，新增本目录截图；后端24文件阶段清单见 C0–C2 提交与报告。

生产入口仍关闭，正常环境不会显示可派发的生成按钮；owned-only 端点没有改为公共入口。测试服务器和 Vite 在交付时停止，仅保留证据及 owned 数据库。无 push / merge / deploy，无自动进入下一业务 Item。

`INITIAL_CLARIFICATION_CONTINUATION_PASS`

`ITEM9_REACT_IMPLEMENTATION_COMPLETE`

`REAL_PRODUCT_SEMANTIC_ACCEPTANCE_PENDING`

`PUBLIC_GENERATE_NOT_ENABLED`

`STOP`

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
