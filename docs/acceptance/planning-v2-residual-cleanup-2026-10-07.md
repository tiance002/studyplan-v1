# Planning V2 — Residual Cleanup Before Refactor（2026-10-07）

## 用户现在能做什么

学习计划路由可以正常打开，主区只显示“学习计划”和“新的学习规划流程正在重构，当前暂不可创建新路线。”。旧生成、运行恢复和有限路线变更 UI 已移除。既有正式路线、学习、总结、Prompt、助手和资源基础服务保留。没有实现 Planning V2，没有新建路线。

## 基线与恢复

- branch：`feat/n1-resource-discovery`。
- start HEAD：`6f62b9e1687ce79b8b3ca4190c0b9b4974323272`。
- 本地 annotated checkpoint：`checkpoint/pre-planning-v2-residual-cleanup`，指向 start HEAD。
- final HEAD：本报告与代码的提交 SHA 见本批最终答复及 `var/planning-residual-cleanup-20261007/final.json`；不使用自引用 SHA。
- 起点受跟踪工作树干净，仅 `.workbuddy/`、`design-preview/` 未跟踪。两个目录未操作。
- 未 reset、切换分支、整树 restore、push、merge、deploy。
- 必要回滚方式：评审后 revert 本批提交；不改写历史，不自动回滚数据库。

## 删除及迁移

### 生产运行时

- `graphs.py` 删除旧长图 `run_planning_graph`、`build_planning_graph`、`_run_generate_and_repair_loop`、`_await_approval`、`_cancel_draft` 及专用 imports/exports。保留 review executor、trace、graph namespace/version guard。
- `nodes.py` 删除已无图 consumer 的 `await_approval`、`cancel_draft_node` wrapper。其他混合内容保护与可靠性节点保留。
- 生产 `planning_demo.py` 删除。相关 source/content/repair 测试响应迁至 `tests/helpers/planning_responses.py`；应用组合根仅装配无 handler 的 `FakeLLM()`，不注册任何旧生成 fallback。
- 旧长图的 repair/decision/cancel/checkpoint 转移夹具迁至 `tests/helpers/retained_planning_graph.py`。没有 app → tests import。
- `plan_change_routes.py` 删除独有 `/api/v1/plan-changes/generate`；`plan_change_schemas.py` 删除 `GeneratedPlanChangeRequest`。OpenAPI 与生成 TS 同步。普通 `/api/v1/plans/generate` 保留明确 fail-closed；scope/认证仍优先。
- 更新 providers 装配说明及 HOLD 模块说明，移除“当前只有 Fake/B3 未实现”等错误时点描述。

### 前端

- `PlanningPage.tsx` 从 831 行旧生成/Draft/Run/历史 UI 收敛为 8 行占位组件。
- 删除 `PlanChanges.tsx`；删除 main 中生成/发布/actor/project wiring。
- 删除 API client 的 `generate`、`generatePlanChange`。其他 read/cancel/decision/publication helpers 保留。
- 删除无 consumer 的旧 planning 样式及 mobile overrides；不重构导航或其他页面。
- package 中旧 `test:progress` 改为 `test:planning`。

### 测试处理

- 删除 19 个旧规划 UI 测试/helper（完整列表见下）。替换为 `planning-placeholder.browser.cjs`：实际 Edge、八种旧缓存状态、刷新、精确占位内容、无交互表单、无 planning/Run/Draft/decision 请求。
- 删除五个旧浏览器 wrapper 测试和 `_run_owned_route_browser` helper；保留各文件独立 API/PG 的 CAS、scope、取消、发布、幂等、历史与 unknown 断言。
- `learning-guidance-pg.browser.cjs` 仅删除旧规划 snapshot 展示分支，保留 guidance/auth/read/relogin/mobile。
- `test_b3f2_planning.py` 删除生成路线长度/task 数/interrupt 的旧业务断言，改成直接构造 reviewed 内容夹具；缺 required node 必须拒绝的内容保护断言保留。
- 旧长图测试全部继续覆盖错误通道覆盖、repair2、非法决定拒绝、编辑重新校验、取消、幂等副作用和版本命名空间。测试夹具的 `TransitionNodes.save_draft_projection` 只测试历史 callback 顺序；无 frozen marker 的历史输入不能代表现代投影正确性。生产 `checked_projection` 未改且仍拒绝 markerless。

## 完全删除文件

- `backend/app/infrastructure/providers/planning_demo.py`
- `frontend/src/features/planning/PlanChanges.tsx`
- `frontend/tests/add-topic-pg.browser.cjs`
- `frontend/tests/add-topic.browser.cjs`
- `frontend/tests/direction-blueprints-pg.browser.cjs`
- `frontend/tests/generated-route-pg.browser.cjs`
- `frontend/tests/generated-route.browser.cjs`
- `frontend/tests/plan-changes-pg.browser.cjs`
- `frontend/tests/plan-changes.browser.cjs`
- `frontend/tests/planning-cancel-pg.browser.cjs`
- `frontend/tests/planning-cancel.browser.cjs`
- `frontend/tests/planning-intent.browser.cjs`
- `frontend/tests/planning-progress.browser.cjs`
- `frontend/tests/planning-recovery.browser.cjs`
- `frontend/tests/run-detail-scope.browser.cjs`
- `frontend/tests/run-detail-scope.html`
- `frontend/tests/run-detail-scope.tsx`
- `frontend/tests/run-history-pg.browser.cjs`
- `frontend/tests/run-history.browser.cjs`
- `frontend/tests/short-generation.browser.cjs`
- `frontend/tests/user-slice.browser.cjs`

生产 Fake 文件的内容保护 fixture 已迁至测试目录，因此其删除不表示删除相应保护覆盖。

## HOLD_FOR_V2（不是 dead references）

| 文件 / 函数 | 旧职责 | 保留职责及暂不能删除的原因 |
|---|---|---|
| `planning_outline.py`：`frozen_pack_is_intact`、`outline_payload`、marker/size helpers | 旧 outline shape/projection | pack digest、provider size、恢复前完整性；nodes/executor/provider 仍引用，不能丢失来源与预算保护 |
| `planning_structure.py`：`check_frozen_structure`、presentation/focus helpers、`_negated_teaching_action` | structure 教学投影 | canonical/source/focus、repair/恢复验证；助手教学合同直接消费否定动作 helper，不能整删 |
| `planning_batches.py`：`freeze_manifest`、`manifest_is_intact`、`attempt_key`、batch runner/merge | 旧分阶段生成 | manifest/hash、独立冻结输入、预算、repair2、receipt/reconciliation、checkpoint 投影交织；本批不拆大文件，公共提交保持关闭 |
| `nodes.py`：generate/validate/repair/save 的混合部分 | 旧 generation nodes | content validation、error channels、bounded repair、保存投影；仍由保留短图和恢复代码引用 |
| `openai_compatible.py`：planning SHAPES、preflight、`generate_structured` 的 planning 分支 | 旧 wire schema/prompt | 与严格 JSON/known-invalid repair、usage/truncation、budget、attempt receipt 共用；删 shape 会使可靠性协议覆盖失真 |
| `PgPlanningExecutor` / runtime factory | 旧短图执行/恢复接线 | checkpoint integrity、manifest/receipt/version/绑定、零重复派发；不代表允许新提交或恢复历史 failed/unknown |
| `generated_plan_changes.py`：`existing_submission`、`validate_generation`、`save_generated`、hash/current helpers | 生成式变更 | idempotency、actor/project、fence、source snapshot、CAS 和发布事务；prepare 已关闭，不能整删 |
| `domain/generated_plan_changes.py`：`added_topic_route`、`compose_generated_draft` | 旧 operation composition | closure/validation、retained history；`PgPlanChanges.context` 仍消费，混合 public read/历史契约，不能当 dead mapping 删除 |
| `application/plan_changes.py`、`practice_changes.py` 的 context/preview/get/decide | 有限变更门面 | scope、diff、CAS、idempotency、用户决定和历史，不依赖旧 selector，不整删 |
| public `PlanChangeContext`、`PlanChangePreviewView`、`GeneratedOperation` | 旧 operation 字段 | 既有历史投影/决定/读兼容混合；不为本次临时制造 DTO |
| frontend client `planChange*` / `preview*` / confirm/cancel；run/runs/cancelRun/draft/current/decide | 已移除 UI 的 API consumer | public read/发布/取消基础，run 有 Summary/Prompt 的非规划 consumer；保留接口基础 |
| `current-learning-loop-pg.browser.cjs` | 默认模式依赖旧生成 UI bootstrap | 混合学习/原文历史/账号隔离；保留现有 e2 分支，默认 bootstrap 当前不可用，NOT RUN，后续用预发布 Plan fixture 统一迁移 |
| retained PG fixtures / generated-change integration cases | 旧生成准备 bootstrap | 内含独立 RLS/CAS/cancel/receipt/publication 保护；本轮未运行 PG、不声称旧 fixture 已可用于新 planner |
| `tests/helpers/planning_responses.py` 与历史 graph helper | 历史协议 Fake 输入 | 仅供 retained content/JSON/预算/恢复反例，不注册生产 fallback，不作为 V2 产品事实 |

因此“删除目标的 dangling reference=0”不等于清除所有旧 planning 字符串。上述保留项有实际保护 consumer；历史 Markdown/evidence 不删除。

## 明确保留的底座

内容 JSON（含 Agent8、AI、Cloud、Python、coding/RAG/workflow）、Stage/LearningUnit/Knowledge/Relation/Practice/Resource/Guidance/Extension、GoalSpec 六类输入事实、PlanDraft/PlanRevision/current read、publication/history、auth/RLS、workspace、assistant/summary/prompt、resource discovery/GitHub/Tavily/SSRF、Worker/Run/Job/Attempt/Receipt、budget/fence/cancel/unknown、seed validation、known JSON repair。没有新 Prompt、V2 数据结构、Compiler 或 API。

## 验证与证据

| 验证 | 状态 | 实际范围 |
|---|---|---|
| Python compile/import | PASS | app + test helpers compile；非规划 auth/workspace/assistant/summary/prompt/resources import smoke |
| API boot / fail-closed | PASS | TestClient lifespan、health/session、认证/scope、generate503；NoSideEffects 拒绝全部 repo/run/job/binding/provider 访问 |
| 当前受影响保护 / contract | PASS | `protected-final.xml`：432 项，包含 request171/shared assistant、Summary/Prompt、source/canonical、JSON/预算/安全/发布/幂等 |
| 历史图可靠性 / adapter | PASS | 57 项历史转移/真实 LangGraph InMemorySaver + 9 项 adapter/content；`retained-graph.xml`，其中更新后的9项另存 `content-fixture-final.xml`；有效唯一用例合计498 |
| 全 backend collection | PASS | `collection-final.log`，无 import/collection error |
| OpenAPI / TS | PASS | freshly exported OpenAPI、npm gen:api，contract consistency 通过 |
| frontend unit/build | PASS | 27 项 npm test；tsc/Vite build；没有安装依赖 |
| 实际 Edge Planning route | PASS | 本机安装 Edge + local HTTP fixture；八种旧缓存状态和 reload；主区只有指定占位，规划相关请求0 |
| 截图结构检查 | PASS | `var/planning-v2-residual-cleanup-20261007/planning-placeholder-edge.png` |
| deleted runtime/frontend references | PASS | 删除入口/import/UI/helper dangling refs 0；`invariants.json`、`deleted-reference-audit.json`，HOLD 与历史文档不计 dead |
| git diff whitespace | PASS | `git diff --check` |
| 保护资产 | PASS | baseline 的459文件 SHA保持；含内容/迁移/助手/账本/.env/上一批证据；保护目录未访问/修改 |
| 真实 PG / checkpoint 服务 | NOT RUN | 本轮要求 compile/API boot/浏览器 fixture，不以 InMemorySaver 代表 PG |
| 真实 provider/search/Reader/RAG | NOT RUN | 本轮没有任何产品调用 |

首轮169项中的31 FAIL保存在 `targeted.xml/log`：历史无 marker 的图测试误走现代 frozen projection，不能因此放宽生产校验。已迁为明确 test-only callback fixture，最终全部相关断言 PASS。初轮 Edge/Vite sandbox EPERM及一次端口超时与获批 host 重试事实保留，不把环境失败当产品PASS。

## 零增量和状态

- 产品真实模型新增0；request/result 均174，cap280，余106。历史请求/回执/failed/unknown不改写、不恢复、不重派。
- 产品搜索、外部 RAG/Reader新增0。
- 普通 generate 的新 Run0/Job0/provider0/PlanMutation0：在依赖访问前拒绝的机械证据；**不是本轮真实 PG 行计数**。
- DB业务写入0、migration新增0，head0025；没有 DBreset/原产品库操作/正式入口/正式Worker/全局配置改动。
- root关键删除判断请求 Sol6.1/xhigh，前端有界执行 Sol6.1/medium、只读审计 Luna/medium；实际解析均 NOT OBSERVABLE，不宣称切换。
- 临时前端验证服务已停止；已有本人受控体验入口未操作。
- 下一安全动作：等待用户 Planning V2 正式 Goal，按其合同决定 HOLD 项统一替换。当前不自动进入该阶段。

**PLANNING_V2_RESIDUAL_CLEANUP_COMPLETE**
**PLANNING_V2_NOT_IMPLEMENTED**
**整体 STAGING_BLOCKED / NOT_READY**
**STOP**
