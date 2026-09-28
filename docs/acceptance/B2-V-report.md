# B2-V 发布边界修复与第一条业务垂直切片 —— 验收报告

- **仓库**：`D:\studyplan`（`origin` = `https://github.com/tiance002/studyplan-v1.git`，分支 `master`）
- **审查基线**：`b9e9cb0716a01084efdcbeb68fc00f7387790c5c`（B2-C 收口报告）
- **执行前 HEAD**：`b9e9cb0716a01084efdcbeb68fc00f7387790c5c`（与基线**一致**），工作树干净
- **本次提交**：`7da6ce1`（代码 + 契约生成物）；本验收报告为紧随其后的 docs 提交
  （`docs/acceptance/B2-V-report.md`）
- **远端落地**：`origin/master` = `668f3bf`（docs）← `932c434`（代码），
  parent = `b9e9cb0`。因本机 `git push` 被代理拦截，改用 GitHub Git Data API 重建提交，
  故远端 SHA 与本地不同，但**内容逐字节等价**（远端 commit 的 `tree` == 本地
  `git rev-parse HEAD^{tree}` == `8491a62a1cf0b83a5acc2f1843c635dd20f1cc16`）。
- **结论**：Goal §一–§八全部完成；**378 测试通过**（0 失败 / 0 跳过）；
  `ruff` / `mypy` / 前端 `tsc -b` 全部干净；真实 PostgreSQL + Fake LLM 跑通
  第一条业务 HTTP 链路。
- **未触碰**：旧目录 `E:\codex_workspace\study-plan` 全程**只读未访问**；
  所有数据库操作仅限 `studyplan_test_*` **临时库**（用后即 `DROP`）；
  未修改任何全局角色属性，未改写已发布的迁移 `0001`–`0003`。

---

## 1. 交付项与达成情况

### §一 目标边界

保持 B1.2 / B2-C 架构（`api → application → domain & ports ← infrastructure`，
由 `tests/unit/test_import_direction.py` AST 机械守卫）。**没有**整体重构、
**没有**新增工作流引擎、**没有**做完整 RAG / 真实模型调优 / 长期记忆 / UI 打磨。
新增的五个模块（`domain/runs`、`ports/runs`、`ports/sessions`、
`application/*`、`api/v1/*`）全部落在既有分层内，`mypy` 62 个源文件无告警。

### §二 发布原子性（P1）

| 要求 | 实现 | 证据 |
|---|---|---|
| 草案状态 + 版本 + 历史切换 + 关系写入 + 发布记录**单事务** | `PgPlanRepository.publish_revision` 的整个写入序列在 `with psycopg.connect(...)` 单事务内；异常自动 ROLLBACK | `test_failed_publish_rolls_back_entirely`、`test_publish_is_single_transaction`（顺序断言 `begin,check_draft,insert_revision,insert_record,update_draft_status,set_current`） |
| 事务内**复核**草案最新状态，不信任调用方旧对象 | 事务开头 `SELECT status, content_hash FROM plan_drafts ... FOR UPDATE` | `test_publish_rejects_stale_object_after_cancel`、`test_publish_rejects_unknown_draft` |
| 已取消 / 已处理草案不得再发布 | DB 状态 ∉ `PUBLISHABLE_DRAFT_STATUSES` → `ConflictError(reason="draft_not_publishable")` | `test_cancel_then_approve_is_rejected`（HTTP 层 409） |
| 更新草案用**状态条件** + 检查**受影响行数** | `UPDATE ... WHERE status = ANY(...)`；`rowcount != 1` 即抛错并回滚 | `test_save_draft_does_not_resurrect_cancelled`、`test_save_draft_rejects_rewrite_of_approved` |
| 成功后 DB 草案必须为 `APPROVED` | 事务内条件更新为 `approved` | `test_successful_publish_reads_back_consistent_draft_and_plan` |
| 任一失败整体回滚（含历史版本状态） | 单事务边界；`superseded` 的 UPDATE 与后续 INSERT 同事务 | `test_failed_publish_rolls_back_entirely` |
| 移除发布后多余的 `save_draft` | `PlanPublicationService.publish` 不再调用 `save_draft`；草案终态更新归入 `publish_revision` | 单元 `test_publish_is_single_transaction`（断言调用序列恰为 `begin,check_draft,insert_revision,insert_record,update_draft_status,set_current`，**不含** `save_draft`） |
| 取消 vs 发布并发 | 行锁串行化，失败方显式报错 | `test_cancel_vs_publish_concurrency_exactly_one_wins`（真实 PG，两线程）+ HTTP 层 `test_concurrent_cancel_and_publish_exactly_one_wins` |

### §三 统一版本快照构建与指纹（P1）

- **唯一入口**：`build_revision_snapshot`（草案包装 `revision_from_draft`），
  定义在 `app/domain/planning/models.py`。生产路径
  （`PlanPublicationService.publish`）与测试（`_build_revision`）**共用**它。
- **每版重新生成 `stage_id`** 并按稳定语义重映射
  `unit_links` / `task_links` / `stage_resources` / `extensions` /
  `task_knowledge_links`。因为 `plan_stages.stage_id` 是**全局主键**，
  复用旧 ID 会在第二版直接主键冲突。
- **指纹只依赖稳定语义字段**：`stage_id` 一律解析为 `stable_key` 后才入哈希，
  因此「同路由、不同 stage_id」得到**同一**指纹。
- 单测：`test_same_route_with_different_stage_ids_has_same_fingerprint`、
  `test_build_revision_snapshot_remaps_all_references`（`unit_links` /
  `task_links` / `stage_resources` / `extensions` / `task_knowledge_links` 全部重映射）、
  `test_publish_carries_unit_and_task_links_and_snapshot`、
  `test_only_mainline_resource_change_creates_new_version`、
  `test_only_extension_change_creates_new_version`、
  `test_production_publish_uses_single_conversion_entry`；
  真实 PG：`test_consecutive_revisions_have_distinct_stage_ids`（`tests/integration/test_pg_plan_repository.py`）；
  历史保留：`test_replanning_keeps_previous_revision_history`（单测）+
  `test_republish_preserves_historical_completion_records`（真实 PG，断言历史
  `summary_attempts` 不被删除、旧版本阶段/单元/资源/扩展仍可完整读回）。

### §四 草案哈希与幂等记录（P1）

- `PlanDraft.content_hash` 与 `PlanRevision.structure_fingerprint` 共用
  同一份 `_structure_payload`，因此**不可能分叉**。至少覆盖：
  `fallback_search_terms`、扩展 `required` / `unit_id`、主线分节与顺序、
  资源来源与版本、任务-知识链接、领域包版本、阶段顺序。
- **复用当前版本时仍持久化幂等结果**（`created=False` 分支同样写
  `plan_publications`），否则同键重放找不到记录会再次进入发布分支。
- 幂等判定顺序：`publish` **先**查幂等键 → 同键同体返回**原结果**
  （即使草案已 APPROVED、路线已推进）→ 同键异体 409。
- 单测 / PG 测试：`test_hash_covers_fallback_search_terms`、
  `test_hash_covers_extension_required_and_unit_id`、
  `test_hash_covers_task_knowledge_links`、
  `test_hash_covers_mainline_section_order`、
  `test_structure_fingerprint_and_draft_hash_share_semantics`、
  `test_reuse_path_persists_idempotency_record`、
  `test_reuse_then_replay_returns_original_without_republishing`、
  `test_historical_idempotency_replayable_after_later_publish`、
  HTTP 层 `test_repeated_confirmation_does_not_republish`、
  `test_same_key_different_body_is_conflict`。

### §五 DB 归属完整性

迁移 `backend/alembic/versions/0004_ownership_integrity.py`（**增量**，
`down_revision = "0003"`；未改写已发布的 0001–0003）：

1. `plan_stages` 增 `UNIQUE (project_id, plan_id, stage_id)`；
   `plan_unit_links` / `plan_task_links` / `stage_resource_assignments` /
   `knowledge_extensions` 的 stage 外键由二元升级为**三元复合 FK**
   `(project_id, plan_id, stage_id)` → 同时禁止「跨项目」与「跨计划」误关联。
2. 新增 `plan_task_knowledge_links`：主键 `link_id`，
   `UNIQUE (project_id, plan_id, task_id, node_id)`，
   复合 FK 指向 `plan_revisions` / `plan_task_links` / `knowledge_nodes`，
   `FORCE ROW LEVEL SECURITY` + `studyplan_app` 授权。
3. `stage_resource_assignments.source_ref` → `public_resource_sources(source_id)`；
   空串在迁移中归一为 `NULL`（否则外键会拦掉"无来源 + 搜索建议"的合法降级）。
4. `ai_runs` 增 `version`（乐观并发）。
5. `downgrade()` 带数据保护（新表有行时拒绝降级）。

- **反例测试**（`tests/integration/test_pg_ownership_integrity.py`，15 例）
  全部使用 **BYPASSRLS 迁移角色**，因此证明约束来自**外键本身**而非 RLS：
  跨计划 stage（单元/任务/资源/扩展各一）、跨项目 stage、不存在的 stage、
  未知 plan 的 stage、孤儿资源分配、孤儿扩展、扩展绑定他计划单元、
  任务-知识跨计划、`source_ref` 不存在 → 全部被数据库拒绝。
- 公共资源**输出前**校验：`resolve_assignment_output`（领域）在
  `GET /plans/drafts/{id}` 与 `GET /plans/current` 上核验「来源存在」+
  「章节属于该来源」；失败时只给搜索建议。
  **落库前**用 `normalize_stage_resources` 做**同一份**判定，把无法核验的
  引用降级（`source_ref` → NULL、丢弃章节、保留搜索建议），
  因此「界面展示的降级」与「数据库里的正式版本」**完全一致**。

### §六 最薄的 B2-V HTTP 路径

| 端点 | 方法 | operationId | 说明 |
|---|---|---|---|
| `/api/v1/plans/generate` | POST | `generate_plan` | 202，返回 `run_id` + `status_url` |
| `/api/v1/runs/{run_id}` | GET | `get_run` | 运行状态投影（`status` / `next_action` / `result_ref`） |
| `/api/v1/plans/drafts/{draft_id}` | GET | `get_plan_draft` | 完整草案 + `draft_hash` + 已核验资源 |
| `/api/v1/plans/drafts/{draft_id}/decision` | POST | `decide_plan_draft` | approve / edit / cancel |
| `/api/v1/plans/current` | GET | `get_current_plan` | 当前正式路线（无则 404） |

- **授权**：`AuthContext` **只**由服务端会话派生 ——
  `Cookie(不透明令牌) → SessionResolverPort.resolve() → AuthContext`。
  请求体 / 查询串 / 请求头中的 `actor_id`、`tenant_id`、项目范围一律
  **不被读取**；`extra="forbid"` 使伪造字段直接 422。
- **先鉴权再访问仓储**：每个端点先 `scope.require_project(project_id)`，
  不通过即 403（不区分「不存在」与「无权限」，避免枚举探测）。
- **组合根**：`app/composition.py` 装配 `AppContainer`；
  `create_app(container=None)` 支持测试注入；缺 `DATABASE_URL` 时
  `plan_service=None`，业务端点明确 **503**（不静默降级到内存实现）。
- **契约**：`contracts/openapi.json` 含 6 条真实路径 / 6 个 operationId /
  38 个 schema；`contracts/examples/v1_examples.json` 增 `plan_decision_response`
  示例；`frontend/src/api/generated/schema.d.ts` 由 `openapi-typescript` 重新生成，
  已包含全部 5 条业务路径（契约漂移门禁 `test_committed_openapi_matches_fresh_export` 通过）。

### §七 真实端到端验收

`backend/tests/e2e/test_b2v_http_end_to_end.py`（17 例，TestClient + 真实 PostgreSQL
+ 注册了处理器的 Fake LLM）：

| 场景 | 测试 |
|---|---|
| 建目标 → 生成 → 运行状态 → 查看 → 编辑 → 重新校验 → 确认 → 回读 | `test_full_chain_generate_edit_approve_readback` |
| 草案展示资源 == 发布后读回资源 | `test_draft_view_and_current_plan_agree_on_resources` |
| 过期哈希确认被拒 | `test_stale_draft_hash_is_rejected` |
| 重复确认不重复发布 | `test_repeated_confirmation_does_not_republish` |
| 同键异体 409 | `test_same_key_different_body_is_conflict` |
| 先取消后发布被拒 / 先发布后取消被拒 | `test_cancel_then_approve_is_rejected`、`test_approve_then_cancel_is_rejected` |
| 取消 vs 发布真并发恰好一个成功 | `test_concurrent_cancel_and_publish_exactly_one_wins` |
| 跨用户 403 / 跨项目 403 / 未认证 401 | `test_other_user_cannot_access_project`、`test_owner_cannot_access_other_project`、`test_unauthenticated_request_is_rejected` |
| 请求体伪造身份 422 | `test_auth_context_cannot_be_spoofed_from_body` |
| 进程重启后恢复 | `test_pending_draft_survives_process_restart` |
| 缺少公共资源显式降级 | `test_missing_public_resource_degrades_explicitly` |
| 重规划保留旧版本与完成记录 | `test_replanning_preserves_history_and_reads_back` |
| 空目标不调模型 | `test_empty_goal_is_rejected_without_calling_model` |
| 未知草案/运行 404 | `test_unknown_draft_and_run_are_not_found` |

**关键一致性断言**（`test_full_chain_...` 第 7 步）：

    HTTP 草案展示内容 == 用户确认内容 == 数据库正式版本 == GET /plans/current 结构

即：草案视图的 `stages` / `unit_links` / `task_links` / `stage_resources`
（含有序章节与搜索建议）/ `extensions` 与发布后 `GET /plans/current` 读回的
结构逐字段一致（阶段 ID 每版重新生成，故按 `stable_key` 对齐后比较引用）。

### §八 执行与交付约束

- 迁移**只在** `studyplan_test_*` 临时库执行（`create_test_database` →
  `alembic upgrade head` → 用后 `DROP DATABASE`）；未触碰旧库 / 生产数据 /
  全局角色属性。
- 全量 `pytest`、真实 PG 测试、真实 LangGraph 测试、`ruff`、`mypy`、
  OpenAPI 漂移门禁、前端 `tsc -b` 全部实际运行，命令与退出码见 §3。
- 未运行项在 §5 显式列出，**没有**把未运行项写成通过。

---

## 2. 变更文件（`7da6ce1`，36 个文件 / +7270 −1284）

**新增（业务代码）**

```
backend/app/domain/runs/models.py            运行投影领域模型（status/next_action 合法组合）
backend/app/domain/runs/__init__.py
backend/app/ports/runs.py                    RunRepositoryPort / PlanningCatalogPort / CatalogIds
backend/app/ports/sessions.py                SessionResolverPort（AuthContext 只能服务端派生）
backend/app/infrastructure/db/run_repository.py     PgRunRepository（乐观并发 version+1）
backend/app/infrastructure/db/planning_catalog.py   PgPlanningCatalog（按 stable_key 幂等物化）
backend/app/infrastructure/db/public_resource_catalog.py  PgPublicResourceCatalog（只读）
backend/app/application/container.py         AppContainer（API 层唯一可见的依赖形状）
backend/app/application/sessions.py          InMemorySessionStore（骨架会话存储）
backend/app/application/draft_projection.py  图产物 → PlanDraft 的唯一投影
backend/app/application/plan_resources.py    资源输出/落库前的核验与降级
backend/app/application/plan_service.py      PlanService（生成/读取/决定编排）
backend/app/composition.py                   组合根（唯一 import infrastructure 装配业务服务）
backend/app/api/v1/deps.py                   容器访问 + 服务端会话派生 AuthContext
backend/app/api/v1/views.py                  领域对象 → DTO 的唯一映射
backend/app/api/v1/routes.py                 五条业务端点
backend/alembic/versions/0004_ownership_integrity.py
```

**新增（测试）**

```
backend/tests/e2e/test_b2v_http_end_to_end.py           17 例（TestClient + 真实 PG）
backend/tests/integration/test_pg_ownership_integrity.py 15 例（BYPASSRLS 反例）
```

**修改**

```
backend/app/domain/planning/models.py          §二/§三/§四：唯一版本入口 + 共享指纹载荷 + decide_draft 顺序
backend/app/domain/resources/curation.py       §五：ResolvedSection/ResolvedAssignment/resolve_assignment_output
backend/app/infrastructure/db/plan_repository.py  状态条件 + 行数检查 + cancel_draft + 任务-知识链接
backend/app/infrastructure/db/__init__.py     导出新仓储实现
backend/app/api/v1/{__init__,schemas}.py      路由导出 + PlanDecisionResponse + 字段语义说明
backend/app/main.py                           容器注入 + 请求 id + 统一错误体 + 注册路由
backend/tests/{unit,integration,contract}/*   新增/修正断言（详见各文件）
contracts/openapi.json                        重新导出（6 路径 / 38 schema）
contracts/examples/v1_examples.json           增 plan_decision_response 示例
frontend/src/api/generated/schema.d.ts        重新生成
pyproject.toml                                ruff: fastapi 依赖注入声明为不可变调用（B008）
```

---

## 3. 执行命令与退出码（真实记录）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `./.venv/Scripts/python.exe -m pytest backend/tests -q` | `0` | **378 passed**，0 failed，0 skipped（2m29s） |
| `./.venv/Scripts/python.exe -m pytest backend/tests -m postgres -q` | `0` | 102 passed |
| `./.venv/Scripts/python.exe -m pytest backend/tests -m "not postgres" -q` | `0` | 276 passed |
| `./.venv/Scripts/python.exe -m pytest backend/tests -m langgraph -q` | `0` | 25 passed（真实 `StateGraph` + Checkpointer） |
| `./.venv/Scripts/python.exe -m pytest backend/tests/e2e -q` | `0` | 17 passed（TestClient + 真实 PG） |
| `./.venv/Scripts/python.exe -m ruff check backend` | `0` | `All checks passed!` |
| `./.venv/Scripts/python.exe -m mypy backend/app` | `0` | `Success: no issues found in 62 source files` |
| `bash scripts/export_openapi.sh` | `0` | 写入 `contracts/openapi.json` |
| `(cd frontend && npm run gen:api)` | `0` | 重新生成 `schema.d.ts`（openapi-typescript 7.13.0） |
| `(cd frontend && npx tsc -b)` | `0` | 前端类型检查通过 |
| `./.venv/Scripts/python.exe -m pytest backend/tests/contract -q` | `0` | 30 passed（含 OpenAPI 漂移门禁、前端类型覆盖、AuthContext 不入请求体） |

环境：Python 3.13.12（`.venv`）、PostgreSQL 16.4 @ `127.0.0.1:5432`、
fastapi 0.141.1 / starlette 1.7.0 / langgraph 1.2.12。
`STUDYPLAN_TEST_PG_DEDICATED` **未设置** → harness 全程只读使用既有
`studyplan_migrator` / `studyplan_app` 角色，**未创建/修改任何全局角色**。

### 测试分布（378）

| 层 | 数量 | 说明 |
|---|---|---|
| `tests/unit` | 199 | 领域规则、图路由、发布编排（fake 仓储）、依赖方向、资源核验 |
| `tests/contract` | 30 | 枚举=契约、DTO/OpenAPI/示例/前端生成物一致、隔离约束 |
| `tests/integration` | 132 | 真实 PG 端口契约、迁移/RLS/归属完整性、应用启动、真实 LangGraph |
| `tests/e2e` | 17 | B2-V HTTP 全链路（TestClient + 真实 PG） |
| **合计** | **378** | 其中 `postgres` 标记 102、`langgraph` 标记 25 |

相对 B2-C 基线 **314 → 378（+64）**：§二–§五 增 21（PG）+ 若干单测，
§六/§七 增 17（e2e）+ 契约与启动测试修正。

---

## 4. 明确修复的真实缺陷（回归可复现）

1. **发布后多余 `save_draft`**：会在「已发布」与「草案状态更新」之间留下窗口，
   失败时留下半发布状态 → 已移除，草案终态更新归入发布事务。
2. **信任调用方旧对象**：旧对象可能在事务外被取消 → 事务内 `FOR UPDATE` 复核 +
   状态条件更新 + 行数检查。
3. **同键重放被误判 409**：`decide_draft` 的统一「草案已处理」前置检查会先于
   幂等判定触发 → 已移除该前置检查，改为各分支自证（`publish` 幂等键优先）。
4. **结构与当前路线一致时幂等结果未落库**：导致同键重放再次进入发布分支 →
   `created=False` 分支同样写 `plan_publications`。
5. **`stage_id` 全局主键冲突**：测试助手的 `_build_draft` 计算了 `run_id` 却
   传了原值（`F841` 掩盖的真缺陷）→ 已改为传入派生值。
6. **未核验的公共资源引用会写库**：`source_ref` 指向不存在的来源会在发布时
   触发外键错误，或（在无外键时）让未核验章节被当成已核验输出 →
   落库前统一降级为搜索建议。
7. **`GET /plans/current` 与草案视图语义分叉风险**：两处视图曾各自映射字段 →
   收敛到 `api/v1/views.py` 的**唯一**映射。

---

## 5. 未运行项（显式登记）

- **未在真实云模型上运行**：本 Goal 明确只用 Fake LLM（`LLM_PROVIDER=fake`）。
  `build_llm` 对未实现的真实 provider **拒绝启动**，因此不存在"以为在用云模型"
  的静默降级。
- **未做前端页面**：只重新生成了类型（`schema.d.ts`）。V1 的 React 页面属后续 Goal。
- **未做完整 RAG / 长期记忆 / 真实资源检索**：`rag_base_url` 等配置存在但无适配器。
- **未做端到端浏览器测试**：`tsc -b` 只做类型检查，未跑 Vite 构建产物或 Playwright。
- **未做多进程 worker**：见 §6。

---

## 6. 尚未实现的能力（诚实登记，供 B3 排期）

1. **真实云模型适配器**：`providers` 只有 `fake`；`SUPPORTED_PROVIDERS = {"fake"}`。
2. **HTTP 路径未驱动真实 `StateGraph` + 持久化 Checkpointer**：生成路径使用
   B1 的**同构解释器** `run_planning_graph`（B1 已机械证明两者转移一致）。
   真实 `StateGraph` + Checkpointer 目前只在 `tests/integration/test_real_langgraph.py`
   被验证。**这不影响本 Goal 的正确性**：`await_approval` 之后没有任何模型调用，
   决策所需的一切（草案正文、哈希、状态、当前版本）都在数据库里，因此
   进程重启可恢复 —— 但"跨进程/多 worker 的图断点续跑"仍需 B3 接入。
3. **登录 / 会话建立**：`SessionResolverPort` 只有进程内实现；
   没有口令校验、会话轮换、撤销、CSRF 令牌校验（`csrf_enabled` 配置存在但未接入）。
   真实部署必须换成 HttpOnly + SameSite + 服务端会话表。
4. **领域包 / 公共资源的写入通道**：`source_pack_key` / `source_pack_version`
   在服务层默认空串（**如实反映"未加载领域包"**），没有 `domain_packs` 的加载器；
   公共资源只有只读目录，没有受审核的写入流程。
5. **局部重规划**：`diff_revisions` 已有（按 `stable_key` 精确匹配），但
   HTTP 上没有"只重规划某阶段"的端点。
6. **未实现的能力不会静默降级**：缺 `DATABASE_URL` → 业务端点 503；
   未知 provider → 启动即失败；未核验资源 → 显式搜索建议。

---

## 7. 下个 Goal（B3）输入

**结论：骨架优化阶段到此为止。** 从 B3 起进入「真实云模型规划 + 资源闭环」。

建议 B3 的最小切片（按依赖排序）：

1. **真实模型适配器 + 提示词契约**：实现 `LLMPort` 的一个真实 provider
   （结构化输出 + 超时 + **不自动重试**；结果未知时走
   `ReconciliationRequiredError` 而不是清洗为成功）。`llm_base_url` /
   `llm_api_key` / `llm_model_id` 配置已就绪。
2. **领域包加载 + 公共资源受审核写入**：把 `domain_packs` 与
   `public_resource_sources` / `public_resource_sections` 从"只读目录"补成
   可发布的输入，使 `source_pack_key` / `source_pack_version` 不再为空，
   并让 §五 的资源核验有真实来源可命中。
3. **多 worker 的图断点续跑**：接入 Postgres Checkpointer + `graph_thread_id`
   （已实现版本隔离），把生成路径从解释器切到真实 `StateGraph`，
   并复用现有的 `ai_runs` 投影做租约与恢复。
4. **认证域**：真实会话（HttpOnly Cookie + 服务端会话表 + CSRF），
   把 `InMemorySessionStore` 替换为持久实现；`AuthContext` 的派生契约不变。
5. **前端首个可用页面**：用已生成的 typed client 打通
   「生成 → 审阅草案 → 编辑 → 确认」的最小界面。

---

## 8. 结论

- Goal §一–§八 **全部完成**，无遗留 P1。
- 发布边界从"看起来原子"变为**可被真实 PG 反例证明的原子**：
  单事务、状态条件、行数检查、幂等键优先、复用也落库。
- 版本快照只有**一个**构造入口，指纹只依赖稳定语义字段，
  「同路由不同 ID → 同指纹」在单测与真实 PG 上双向验证。
- 第一条业务垂直切片**真实接通**：HTTP → 应用服务 → 端口 → PostgreSQL，
  授权来自服务端会话，项目归属先校验后访问。
- 最关键的验收断言成立：**界面展示 == 用户确认 == 数据库正式版本 == 读回结构**。
