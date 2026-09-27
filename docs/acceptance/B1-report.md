# B1 验收报告：新骨架、领域契约与 Graph 最小演练

> 日期：2026-09-27 · 批次：B1（含 **B1.1 缺陷修复轮**）· 依据：`docs/design-package/IMPLEMENTATION_PLAN.md` §5
> **Each item below carries source/test evidence. Unverified items are marked explicitly.**

> **本文件已按 B1.1 修复轮更新**：B1 复审发现的 P1 正确性缺陷、真实 LangGraph 验收、
> PostgreSQL/RLS 验收、启动安全门禁均已在本轮完成。见 §A（修复轮纪要）与各节更新。

---

## 0. 一句话结论

B1 交付了**可独立运行、可机械验证的骨架**。B1.1 修复轮进一步：
**211 个测试全绿**（B1 基线为 104）、Ruff 干净、mypy 干净（38 文件 0 错误）、
**真实 LangGraph `StateGraph` + InMemorySaver/PostgresSaver 验收通过**、
**PostgreSQL 迁移 + RLS 越权反例通过**、**跨进程 checkpoint 恢复通过**、
**生产启动安全门禁接入组合根并通过真实应用工厂验证**。
`domain` / `ports` / `core` 三层不依赖任何框架（由 AST 测试机械保证）。
**未实现**业务路由、真实模型 —— 这些属 B2/B3。

---

## A. B1.1 修复轮纪要（本轮新增）

### A.1 本轮发现并修复的缺陷

| # | 严重度 | 缺陷 | 根因 | 修复 |
|---|---|---|---|---|
| A1 | P1 | **生成阶段错误被后续节点冲掉**：空纲要/空节点/空单元仍被判为有效 | `generation_errors` 是普通覆盖字段，`build_dependencies_and_units`/`propose_practice` 用空列表覆盖了 outline 写入的错误 | 新增 `_extend_generation_errors`：生成阶段**累加**错误；仅 `repair_content` 成功时显式覆盖清空 |
| A2 | P1 | **`validation_errors` 用 `operator.add` reducer**，repair 返回空表无法清空旧错误 | LangGraph reducer 语义 | 全部错误字段改为**普通覆盖字段**；拆出 `input_errors`/`generation_errors`/`structure_errors` 三通道；`validation_errors` 仅为聚合视图，`validation_history` 仅审计 |
| A3 | P1 | **`await_approval → apply_decision` 未接入真实执行路径** | 真实 `StateGraph` 缺该边 | `build_planning_graph` 补齐 `await_approval → apply_decision → route_after_decision`，并支持结构化 `Command(resume={...})` |
| A4 | P1 | **graph_version 不参与 checkpoint 命名空间**，跨版本恢复会串状态 | LangGraph checkpoint 仅按 `thread_id` 索引 | 新增 `graph_thread_id(run_id, graph_version)` 把版本编入 `thread_id`，并加 `assert_resumable` / `GraphVersionMismatchError` 显式守卫 |
| A5 | P1 | **迁移 `downgrade()` 数据保护被 FORCE RLS 绕过**：有数据也能降级 | migrator 无上下文时 `SELECT count(*)` 被 RLS 过滤为 0 | 迁移角色授予 `BYPASSRLS`（其本就是 DDL owner），应用角色显式 `NOBYPASSRLS`；downgrade 遍历**全部**业务表并 `RAISE EXCEPTION` 拒绝 |
| A6 | P1 | **`_infer_evidence_grade` 把 repo_url/commit/sha/ci 当已核验** | 用关键词与 URL 形态判级，可被自述伪装 | 只认平台真实核验记录 `VerificationRecord`（`verification_method`/`verified_at`/`result`/`evidence_ref`）；用户文本/URL/未核验哈希一律 `reported` |
| A7 | P1 | **`PlanPublicationService` 幂等未比对请求体**，同键异体不报 409；发布非单事务；取消草案可发布 | 领域服务缺状态/体指纹校验 | 新增 `PublishRecord` + `body_fingerprint`；发布前查草案状态、`verify_hash`、版本校验；`publish_revision` 端口要求单事务；新增 `PlanRevision.version` 属性 |
| A8 | P1 | **启动安全守卫未被真实启动路径调用** | `assert_not_fake_in_production` 无人调用 | 新增 `core/startup_guard.validate_startup_security` 并在 `create_app()` 组合根调用；生产拒绝 Fake/默认密钥/空 DB/内存 Checkpointer/内存仓储/未实现 provider |
| A9 | P2 | **`order_index` 静默整数截断**：`3.7`→3、`True`→1 | `int(raw)` 强转 | 新增 `_strict_int`：仅接受真正 `int`（排除 `bool`），其余报错 |
| A10 | P2 | `core` 误 import `infrastructure`（依赖方向泄漏） | startup_guard 引用 infra 常量 | 拆分为 core 侧独立常量 + 契约测试机械保证两处一致 |

### A.2 本轮修改文件

**修改**：
`backend/app/agent_workflows/{state,nodes,graphs}.py`、
`backend/app/agent_workflows/validators.py`、
`backend/app/domain/practice/models.py`（证据等级 + `VerificationRecord`）、
`backend/app/domain/planning/models.py`（发布一致性 + `PublishRecord` + `PlanRepositoryPort` 事务契约）、
`backend/app/domain/reflections/models.py`（payload 安全规整）、
`backend/app/ports/repository.py`（端口分工说明）、
`backend/app/main.py`（组合根安全门禁 + 惰性 `app`）、
`backend/alembic/versions/0001_initial_schema.py`（downgrade 数据保护 + RLS）、
`backend/tests/unit/{test_plan_validators,test_graph_workflows,test_import_direction,test_domain_invariants,test_security_boundaries}.py`、
`backend/tests/contract/{test_isolation_contract,test_contract_consistency}.py`、
`pyproject.toml`、`scripts/test.sh`、`frontend/package.json`、`contracts/openapi.json`。

**新增**：
`backend/app/core/startup_guard.py`、
`backend/tests/pg_harness.py`、
`backend/tests/unit/test_evidence_grade.py`（20 例）、
`backend/tests/unit/test_plan_publication.py`（18 例）、
`backend/tests/integration/test_real_langgraph.py`（21 例，真实 `StateGraph` + InMemorySaver）、
`backend/tests/integration/test_pg_migration_rls.py`（12 例）、
`backend/tests/integration/test_graph_recovery_pg.py`（4 例，跨进程 PostgresSaver）、
`backend/tests/integration/test_startup_guard.py`（9 例，真实应用工厂）、
`frontend/package-lock.json`、`frontend/src/api/generated/schema.d.ts`。

---

## 1. changed files

### 1.1 本批次新建（全部为 `new-authored`，见 `docs/migration/source-provenance.md`）

| 路径 | 行数 | 职责 |
|---|---|---|
| `pyproject.toml` | — | 依赖声明（含 `agent` / `postgres` / `dev` extras） |
| `backend/alembic.ini` | — | 纯 ASCII；DSN 走 `STUDYPLAN_MIGRATION_DSN` |
| `backend/alembic/env.py` | — | 迁移环境；迁移角色与应用角色分离 |
| `backend/alembic/script.py.mako` | — | 迁移模板 |
| `backend/alembic/versions/0001_initial_schema.py` | — | **新版独立基线**（不复用旧 0001） |
| `backend/app/domain/practice/models.py` | 400+ | 实践项目 / 任务 / Prompt 修订 / 成果验收 |
| `backend/app/ports/__init__.py` | — | Ports 导出 |
| `backend/app/ports/llm.py` | — | `LLMPort` + `LLMResult` + `LLMFailure` |
| `backend/app/ports/rag.py` | — | `RAGPort` + `Evidence` + `Citation` |
| `backend/app/ports/resource_index.py` | — | `ResourceIndexPort` + `ResourceQuery` |
| `backend/app/ports/graph_runner.py` | — | `GraphRunnerPort` + start/resume 请求 |
| `backend/app/ports/repository.py` | — | `RepositoryPort`（全部方法带 scope） |
| `backend/app/agent_workflows/_msgpack_guard.py` | — | 在 import langgraph 前设 `LANGGRAPH_STRICT_MSGPACK` |
| `backend/app/agent_workflows/__init__.py` | — | 首行导入 guard |
| `backend/app/agent_workflows/state.py` | — | `PlanningState` / `ReviewState`（最小化） |
| `backend/app/agent_workflows/validators.py` | — | 确定性结构校验（无环/顺序/关联/验收/软上限） |
| `backend/app/agent_workflows/nodes.py` | — | 节点实现 + 路由函数 |
| `backend/app/agent_workflows/graphs.py` | — | 解释器 + 真实 `StateGraph` 装配 |
| `backend/app/infrastructure/providers/fake.py` | — | Fake LLM（明确失败，不静默成功） |
| `backend/app/infrastructure/providers/__init__.py` | — | provider 装配（唯一出口，缺凭据拒绝启动） |
| `backend/app/infrastructure/{db,checkpointer,worker,external}/__init__.py` | — | 契约说明占位 |
| `backend/app/api/__init__.py`、`api/v1/__init__.py` | — | HTTP 层占位 |
| `backend/app/application/__init__.py` | — | 应用层占位 |
| `backend/app/main.py` | — | FastAPI 工厂 + `/healthz` |
| `backend/tests/unit/test_domain_invariants.py` | — | 领域不变量 |
| `backend/tests/unit/test_plan_validators.py` | — | 校验器逐规则 |
| `backend/tests/unit/test_graph_workflows.py` | — | 三张图状态转移 |
| `backend/tests/unit/test_security_boundaries.py` | — | 越权 / 假身份 / fake 误用 |
| `backend/tests/unit/test_import_direction.py` | — | 依赖方向（AST 机械保证） |
| `backend/tests/unit/conftest.py`、`backend/tests/__init__.py` 等 | — | 测试基建 |
| `backend/tests/contract/test_isolation_contract.py` | — | 不依赖 E 盘的机械证明 |
| `backend/tests/contract/test_contract_consistency.py` | — | 枚举 = 契约 |
| `backend/tests/integration/test_app_boot.py` | — | 应用可独立启动 + OpenAPI |
| `contracts/openapi.json` | — | 导出的契约（派生物） |
| `contracts/examples/v1_examples.json` | — | 由 DTO 校验的示例 |
| `frontend/{package.json,vite.config.ts,tsconfig.json,index.html}` | — | Vite/TS/React 骨架 |
| `frontend/src/main.tsx`、`frontend/src/api/README.md` | — | 前端入口与契约铁律 |
| `scripts/test.sh`、`scripts/dev.sh` | — | 安全测试/启动入口 |
| `docs/design-package/*` | — | 设计基线入库 |
| `docs/migration/*`、`docs/adr/*` | — | B0 交付物（见 B0 报告） |

### 1.2 本批次修改

| 路径 | 变更 |
|---|---|
| `README.md` | 从 pre-B0 描述更新为 B0 完成 + B1 骨架就绪；补不变量清单与文档索引 |

### 1.3 未改动（遵守约束）

- `E:\codex_workspace\study-plan` —— **一个字节都未写**（见 §4 复核）。
- `D:\studyplan` 原有的 `core/`、`domain/` 既有文件 —— **未覆盖、未删除**，
  仅新增 `domain/practice/`。

---

## 2. commands

| # | 命令 | 用途 |
|---|---|---|
| 1 | `git --no-optional-locks -C E:/codex_workspace/study-plan rev-parse HEAD` | 记录旧 HEAD（只读） |
| 2 | `git --no-optional-locks -C E:/codex_workspace/study-plan status --porcelain=v1` | 确认旧工作树 clean |
| 3 | `git --no-optional-locks -C E:/codex_workspace/study-plan for-each-ref …` | 找未推送分支 |
| 4 | `grep -rn "invit" -i backend/app frontend/src alembic` | 确认邀请码已清理 |
| 5 | `sha256sum <files>` | 计算来源溯源哈希 |
| 6 | `python -m venv .venv`（仓库内隔离） | 不复用旧 `.venv` |
| 7 | `.venv/Scripts/python.exe -m pytest backend/tests -p no:cacheprovider` | 运行全部测试（unit+contract+integration） |
| 8 | `.venv/Scripts/python.exe -c "…create_app().openapi()"` | 导出 OpenAPI |
| 9 | `.venv/Scripts/python.exe -m ruff check backend` | 静态检查 |
| 10 | `.venv/Scripts/python.exe -m mypy backend/app` | 类型检查（38 文件 0 错误） |
| 11 | `.venv/Scripts/python.exe -m pytest backend/tests/integration/test_real_langgraph.py` | 真实 LangGraph（InMemorySaver） |
| 12 | `.venv/Scripts/python.exe -m pytest backend/tests/integration/test_graph_recovery_pg.py` | 跨进程 Postgres Checkpointer 恢复 |
| 13 | `.venv/Scripts/python.exe -m pytest backend/tests/integration/test_pg_migration_rls.py` | 真实 PG 迁移 + RLS 反例 |
| 14 | `cd frontend && npm install` | 前端依赖（生成 lockfile + 平台二进制） |
| 15 | `cd frontend && npx openapi-typescript ../contracts/openapi.json -o src/api/generated/schema.d.ts` | 生成 TS client |
| 16 | `cd frontend && npm run build` | `tsc -b && vite build` 构建通过 |
| 17 | `git diff --check` | 空白/EOF 检查（无问题） |
| 18 | `git --no-optional-locks -C E:/codex_workspace/study-plan status --porcelain=v1` | 复核旧工程仍 clean |

> ⚠️ 全部命令在 Windows Git Bash 下执行。**未在 E 盘运行任何安装、迁移、测试或启动脚本。**
> PostgreSQL 验收**只**创建 `studyplan_test_*` 临时库；不触碰任何既有数据库。

---

## 3. results

### 3.1 测试结果（核心证据，B1.1 更新）

```
$ .venv/Scripts/python.exe -m pytest backend/tests -p no:cacheprovider
........................................................................ [ 34%]
........................................................................ [ 68%]
...................................................................      [100%]
211 passed in 55.14s
```

```
$ .venv/Scripts/python.exe -m ruff check backend
All checks passed!

$ .venv/Scripts/python.exe -m mypy backend/app
Success: no issues found in 38 source files
```

**测试分布（B1.1）**：

| 组 | 数量 | 覆盖 |
|---|---|---|
| `unit/test_domain_invariants.py` | ~25 | 进度语义、依赖无环、稳定键、SSRF、偏好优先级、产品约束 |
| `unit/test_plan_validators.py` | 25 | 校验器每条规则"违反即失败"证明 + **非整数 order_index 严格拒绝** |
| `unit/test_graph_workflows.py` | 26 | 三通道错误分离、修复上限=2、空纲要/空节点失败、历史不影响当前校验、非法决定 |
| `unit/test_plan_publication.py` | **18** | 幂等同键同体复用/同键异体 409、取消不发布、hash/版本冲突、单事务全或无、历史保留 |
| `unit/test_evidence_grade.py` | **20** | 反伪装：文本/URL/未核验哈希恒为 reported；仅真实核验为 verified；评审链独立 |
| `unit/test_security_boundaries.py` | 14 | 越权 403、假身份 TypeError、错误码映射、fake 生产禁用 |
| `unit/test_import_direction.py` | 6 | domain/ports/core 零框架依赖、guard 首行、无绕过 |
| `contract/test_isolation_contract.py` | 7 | 无旧路径/env 前缀/软链/本地数据泄漏 |
| `contract/test_contract_consistency.py` | **14** | 枚举=契约、**provider 闭集 core/infra 一致** |
| `integration/test_app_boot.py` | 6 | 应用可启动、operationId 唯一、OpenAPI 可导出 |
| `integration/test_startup_guard.py` | **9** | **真实应用工厂**拒绝 Fake/默认密钥/空DB/内存Checkpointer/内存仓储/未实现 provider |
| `integration/test_real_langgraph.py` | **21** | 真实 `StateGraph` + InMemorySaver 的 A–L 场景 |
| `integration/test_graph_recovery_pg.py` | **4** | **跨进程** PostgresSaver 恢复（条款 J）、重复 resume、线程隔离 |
| `integration/test_pg_migration_rls.py` | **12** | 迁移可执行、全表 FORCE RLS、越权读写拒绝、降级数据保护（真实 PG） |

### 3.1.1 真实 LangGraph 验收（Goal §4，逐条）

安装版本：`langgraph 1.2.12` / `langgraph-checkpoint-postgres 3.1.2` / `psycopg 3.3.6`。
先用 `InMemorySaver` 跑真实图，再用**独立 PostgreSQL Checkpointer** 持久化验收。

| 条款 | 场景 | 结果 |
|---|---|---|
| A | 合法计划 → interrupt 等待确认 | ✅ `test_A_valid_plan_interrupts` |
| A2 | 空学习目标 → 不调用模型、直接失败 | ✅ `test_A2_empty_goal_fails_without_model_call` |
| B | 结构非法 → 修复 ≤ 2 次 | ✅ `test_B_repairs_at_most_twice` |
| C | 修复成功 → 清空旧错误 | ✅ `test_C_repair_clears_old_errors` |
| D | approve → 发布 | ✅ `test_D_approve_publishes` |
| E | edit → 重新校验、再次等待 | ✅ `test_E_edit_revalidates_and_rewaits` |
| F | cancel → 不产生计划 | ✅ `test_F_cancel_produces_no_plan` |
| G | 非法决定 → 不会误发布 | ✅ 参数化 5 例 |
| H | 同 thread_id 真实恢复 | ✅（InMemory + PG） |
| I | 重复 resume → 无重复副作用 | ✅（含跨进程） |
| J | **杀进程+重启仍恢复 `waiting_user`** | ✅ `test_J_cross_process_recovery_of_waiting_user`（子进程写 checkpoint 后退出，主进程 `Command(resume="approve")` 恢复） |
| K | 不同 graph_version 按约定处理 | ✅ 版本编入 `thread_id` + `assert_resumable` 守卫 |
| L | checkpoint 与业务草案不一致 → 不得声称可确认 | ✅ 过期草案 → 显式冲突 |

**关键点**：resume 用真实 `Command(resume=...)` 驱动；解释器路径仅作快速单测工具，
两套场景一致。`graph_version` 不放入 configurable 而编入 `thread_id`（否则不生效）。

### 3.1.2 PostgreSQL 与 RLS 验收（Goal §7）

在**全新临时库** `studyplan_test_*` 上执行 `alembic upgrade head`（不触碰任何既有库）：

| 断言 | 结果 |
|---|---|
| 迁移可干净执行 | ✅ |
| 所有私有表 `ENABLE` + `FORCE ROW LEVEL SECURITY` | ✅ |
| 每张私有表都有归属策略（project/actor/run scope） | ✅ |
| 缺授权上下文 → 默认拒绝（0 行） | ✅ |
| 跨项目读 / 跨项目写 / 跨主体读 均被拒绝 | ✅ |
| 应用角色**无 DDL**、不可绕过 RLS（`NOBYPASSRLS`） | ✅ |
| 迁移角色与应用角色**不同**（migrator `BYPASSRLS`，app 否） | ✅ |
| 有业务数据时降级被拒绝 | ✅ |
| 空库降级成功 | ✅ |

### 3.2 关键实证（不是声称）

| 断言 | 证据 |
|---|---|
| domain 层零框架依赖 | `test_domain_does_not_import_frameworks` 通过（AST 扫描） |
| core 层不依赖 infrastructure | `test_core_does_not_import_domain_or_frameworks` 通过 |
| `LANGGRAPH_STRICT_MSGPACK` 在 langgraph 前生效 | `test_agent_workflows_imports_msgpack_guard_first` 通过；运行时实测值 `true` |
| 修复上限恰好 2 次 | `test_repair_stops_at_two_attempts` 断言 `visited.count("repair_content") == MAX_REPAIR_ATTEMPTS` |
| 生成失败不被空结构掩盖 | `test_generation_failure_not_masked_by_empty_structure` 通过 |
| 修复成功清空旧错误 | `test_repair_clears_old_structure_errors` / `test_C_repair_clears_old_errors` 通过 |
| interrupt 前不提交 | `test_interrupt_precedes_side_effects` 断言 `committed == []` |
| cancel 不产生结果 | `test_cancel_does_not_commit` 断言 `result_id == ""` |
| 跨进程恢复 `waiting_user` | `test_J_cross_process_recovery_of_waiting_user`（PG Checkpointer，子进程退出后主进程 resume） |
| 生产拒绝 Fake / 静默降级 | `test_create_app_rejects_fake_llm_in_production`（真实 `create_app()`）等 9 项 |
| 证据不可伪装为已核验 | `test_user_text_is_always_reported`（10 例参数化）等 20 项 |
| 同键异体发布 → 409 | `test_repeated_publish_same_key_different_body_is_409` 通过 |
| AI 不能独立验收 | `test_prompt_review_pass_is_not_acceptance` / practice 域：`ReviewerKind.MODEL` → `ValidationAppError` |
| 应用无 Postgres 也能启动 | `test_app_boots_without_database_or_network` 通过 |
| operationId 唯一 | `test_openapi_has_no_duplicate_operation_ids` 通过 |
| SSRF 防护生效 | `require_safe_url("http://169.254.169.254/...")` → `ValidationAppError` |
| 前端可构建 + 生成 TS client | `npm run build` 成功；`openapi-typescript` 生成 `schema.d.ts` |
| 产品约束 | 实测 `CredentialPolicy(min=6, max=12, invite=False)` |

### 3.3 与验收条款的对应（B1.1 更新）

| B1 验收条款 | 状态 | 证据 |
|---|---|---|
| 目录不依赖 E 盘而启动 | ✅ | `test_isolation_contract.py` 7 项全通过；实测导入成功 |
| 只用 Fake 的断点可跨进程恢复 | ✅ **已完成** | `test_graph_recovery_pg.py`：独立 PG Checkpointer，子进程中断→主进程 `Command(resume=...)` 恢复 |
| run 越权拒绝 | ✅ | `test_auth_context_denies_foreign_project` 等 4 项 |
| OpenAPI 无重复 operationId | ✅ | `test_openapi_has_no_duplicate_operation_ids` |
| 前端可生成 TypeScript client | ✅ **已完成** | `npm install` + `npm run build` 成功；`openapi-typescript` 生成 `frontend/src/api/generated/schema.d.ts` |
| 只引用 Fake provider | ✅ | `infrastructure/providers` 仅实现 fake；生产配置真实 provider 时**拒绝启动**（真实工厂验证） |
| 真实 LangGraph 转移/暂停/恢复/幂等提交 | ✅ **已完成** | `test_real_langgraph.py` 21 项（InMemorySaver）+ `test_graph_recovery_pg.py` 4 项（PostgresSaver） |
| PostgreSQL 最小安全验收（RLS） | ✅ **已完成** | `test_pg_migration_rls.py` 12 项（真实 PG 16.4 临时库） |


---

## 4. 隔离复核（B0 约束的再次确认）

```
$ git --no-optional-locks -C E:/codex_workspace/study-plan rev-parse HEAD
1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1        # 与 B0 开始时一致

$ git --no-optional-locks -C E:/codex_workspace/study-plan status --porcelain=v1
(空)                                             # 工作树仍 clean
```

✅ **E 盘 Git HEAD 与工作树无意外变化。**

---

## 5. known risks（B1.1 更新）

| # | 风险 | 等级 | 现状 / 缓解 |
|---|---|---|---|
| R1 | ~~跨进程 checkpoint 恢复未演练~~ | — | ✅ **已消除**：独立 PG Checkpointer 跨进程恢复通过（条款 J） |
| R2 | ~~图逻辑未跑在真实 `StateGraph` 上~~ | — | ✅ **已消除**：真实 `StateGraph` + InMemorySaver/PostgresSaver 21+4 项通过；解释器与框架行为一致性由同场景双测保证 |
| R3 | ~~TS client 未实际生成~~ | — | ✅ **已消除**：`npm install` + `openapi-typescript` 生成 `schema.d.ts` 并入库 |
| R4 | ~~新迁移基线未在真实 Postgres 上跑过~~ | — | ✅ **已消除**：`studyplan_test_*` 临时库执行 `alembic upgrade head` 通过 |
| R5 | ~~`ai_run_events` / `ai_provider_attempts` 无归属策略~~ | — | ✅ **已消除**：迁移补齐全部私有表 FORCE RLS + 归属策略 |
| R6 | ~~前端未构建验证~~ | — | ✅ **已消除**：`npm run build`（tsc + vite）通过 |
| R7 | **真实模型 provider 存在性仍 unverified** | 中 | 沿用 B0 结论；生产配置真实 provider 时**明确拒绝启动**；B3 处理 |
| R8 | 6–12 位密码上限低于常见建议 | 低 | 用户既定约束；已用 Argon2id 高成本参数 + 限流要求补偿（ADR-0006 记录取舍） |
| R9 | 发布事务的单事务语义**尚无 PG 实现**，当前由领域端口契约 + 内存实现验证 | 中 | B2 实现 `PlanRepositoryPort` 的 PG 版本时，**必须**用 DB 唯一约束 `(project_id, idempotency_key)` 落幂等，不得 check-then-write |
| R10 | mypy 采用宽松起步配置（未开 `strict`） | 低 | 38 文件当前 0 错误；严格化随 B2/B3 逐步推进 |

---

## 6. next B1 input（进入 B2 的输入）

**B2 目标**：知识与计划业务域 —— 知识节点/关系/单元、路径草案与发布、版本、进度、
实践任务与知识多对多、偏好/资源表、迁移与权限。

**B2 必须先做（承自 B1/B1.1 的未完成项）**：

1. **实现 `PlanRepositoryPort` 的 PostgreSQL 版本**（R9）：单事务发布 +
   `(project_id, idempotency_key)` 唯一约束；契约测试覆盖内存与 PG 两实现。
2. **实现业务 API 路由**（B2 范围）：覆盖 OpenAPI operationId 唯一性测试。
3. **`0002_business_domain.py` 业务表**：按设计 §3 补齐 `knowledge_nodes` /
   `knowledge_relations` / `learning_units` / `unit_node_links` / `plan_stages` /
   `plan_unit_links` / `plan_task_links` / `unit_progress` / `practice_*` /
   `preferences` / `resource_records`。**不要**改 `0001`（历史迁移不可改写）。
4. **真实模型 provider**（B3 范围）：`SUPPORTED_PROVIDERS` 已收敛于 `core` 与
   `infrastructure` 两处并由契约测试机械保证一致。

**B2 的验收情景**（设计 §5）：使用固定示例数据完成
「创建 → 草案 → 确认 → 跳过 → 重新规划 → 进度保留」，
且**同一计划草案重复确认不能重建两份**、**编辑必须重新验证**。

**B2 明确不做**：真实模型（B3）、完整 RAG（独立项目）、UI（B6）、图谱、长期记忆。

### B2 准入结论

**准入通过。** B1 复审提出的 P1 缺陷（状态错误、确认流程、证据可信度、发布一致性、
迁移与 RLS、启动门禁）已全部修复并有失败反例测试；真实 LangGraph、PostgreSQL/RLS、
跨进程 checkpoint 恢复均已实测通过。剩余未完成项（PG 版发布仓储、业务 API、业务表）
均属 B2 范畴且已在 §6 列明，不构成 B2 准入阻塞。

---

## 7. rollback

**推荐方式（安全，可逆）**：B1 及本轮修复均已提交到 Git，直接按 commit 粒度回退，
不使用任何删除命令：

```bash
cd D:/studyplan
# 查看本批次提交
git log --oneline
# 方式 A：撤销某次提交的改动（保留历史，生成新 commit）
git revert <commit-sha>
# 方式 B：把工作区恢复到某个已知良好提交（仅当无未保存改动时）
git switch --detach <good-sha>
# 方式 C：回到 B1 之前的基线（首个 commit 之前不可回退时使用 B0 基线 tag）
git tag -l 'b0-*' 'b1-*'
```

> ⚠️ **不要**使用 `rm -rf backend/... frontend/...` 之类的目录删除命令。
> 那些目录下可能已包含用户自行添加的内容，删除不可逆。
> 如需彻底重置，请新建目录重新 `git clone`，而不是就地删除。

**回退不需要触碰 E 盘**：本批次未向 E 盘写入任何内容，
且 `docs/migration/source-provenance.md` 已证明无文件来自 E 盘复制。
B0 交付物（`docs/migration/`、`docs/adr/`）可独立保留。

**数据库回退**：业务库回退**不用**删表。若 `0001` 已在真实环境使用，
**不得**改写历史迁移，应新增后续修复迁移（见 §6 第 3 条与 `alembic/versions/`）。
`downgrade()` 内置数据保护：任一业务表仍有数据即拒绝破坏性回退。
