# B1 验收报告：新骨架、领域契约与 Graph 最小演练

> 日期：2026-09-27 · 批次：B1 · 依据：`docs/design-package/IMPLEMENTATION_PLAN.md` §5
> **Each item below carries source/test evidence. Unverified items are marked explicitly.**

---

## 0. 一句话结论

B1 交付了**可独立运行、可机械验证的骨架**：104 个测试全绿，`domain` / `ports` / `core`
三层不依赖任何框架（由 AST 测试机械保证），三张图的转移逻辑（修复上限、interrupt 位置、
取消语义）已被单元测试证明。**未实现**业务路由、真实模型、真实数据库 —— 这些属 B2/B3。

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
| 7 | `.venv/Scripts/python -m pytest` | 运行全部测试 |
| 8 | `.venv/Scripts/python -c "…create_app().openapi()"` | 导出 OpenAPI |

> ⚠️ 全部命令在 Windows Git Bash 下执行。**未在 E 盘运行任何安装、迁移、测试或启动脚本。**

---

## 3. results

### 3.1 测试结果（核心证据）

```
$ .venv/Scripts/python -m pytest
........................................................................ [ 69%]
................................                                         [100%]
104 passed, 1 warning in 13.43s
```

（warning 来自 FastAPI TestClient 对 httpx 的弃用提示，与本项目代码无关。）

**测试分布**：

| 组 | 数量 | 覆盖 |
|---|---|---|
| `unit/test_domain_invariants.py` | ~25 | 进度语义、依赖无环、稳定键、SSRF、偏好优先级、产品约束 |
| `unit/test_plan_validators.py` | 16 | 校验器每条规则的"违反即失败"证明 |
| `unit/test_graph_workflows.py` | 15 | 修复上限=2、interrupt 前无副作用、cancel 不提交、edit 重校验、Fake 诚实性 |
| `unit/test_security_boundaries.py` | 14 | 越权 403、假身份 TypeError、错误码映射、fake 生产禁用 |
| `unit/test_import_direction.py` | 6 | domain/ports/core 零框架依赖、guard 首行、无绕过 |
| `contract/test_isolation_contract.py` | 7 | 无旧路径/env 前缀/软链/本地数据泄漏 |
| `contract/test_contract_consistency.py` | 12 | 7 个枚举逐值与设计 §8 一致、next_action 不泄露节点名 |
| `integration/test_app_boot.py` | 6 | 应用可启动、operationId 唯一、OpenAPI 可导出、无旧形态路由 |

### 3.2 关键实证（不是声称）

| 断言 | 证据 |
|---|---|
| domain 层零框架依赖 | `test_domain_does_not_import_frameworks` 通过（AST 扫描） |
| `LANGGRAPH_STRICT_MSGPACK` 在 langgraph 前生效 | `test_agent_workflows_imports_msgpack_guard_first` 通过；运行时实测值 `true` |
| 修复上限恰好 2 次 | `test_repair_stops_at_two_attempts` 断言 `visited.count("repair_content") == MAX_REPAIR_ATTEMPTS` |
| interrupt 前不提交 | `test_interrupt_precedes_side_effects` 断言 `committed == []` |
| cancel 不产生结果 | `test_cancel_does_not_commit` 断言 `result_id == ""` |
| AI 不能独立验收 | `test_security_boundaries` / practice 域实测：`ReviewerKind.MODEL` → `ValidationAppError` |
| 应用无 Postgres 也能启动 | `test_app_boots_without_database_or_network` 通过 |
| operationId 唯一 | `test_openapi_has_no_duplicate_operation_ids` 通过 |
| SSRF 防护生效 | `require_safe_url("http://169.254.169.254/...")` → `ValidationAppError` |
| 产品约束 | 实测 `CredentialPolicy(min=6, max=12, invite=False)` |

### 3.3 与验收条款的对应

| B1 验收条款 | 状态 | 证据 |
|---|---|---|
| 目录不依赖 E 盘而启动 | ✅ | `test_isolation_contract.py` 7 项全通过；实测导入成功 |
| 只用 Fake 的断点可跨进程恢复 | ⚠️ **部分** | 解释器已验证 resume 语义；**跨进程**恢复需 Postgres Checkpointer（属 B2，`langgraph-checkpoint-postgres` 已在 extras 声明但未安装/未演练） |
| run 越权拒绝 | ✅ | `test_auth_context_denies_foreign_project` 等 4 项 |
| OpenAPI 无重复 operationId | ✅ | `test_openapi_has_no_duplicate_operation_ids` |
| 前端可生成 TypeScript client | ⚠️ **部分** | OpenAPI 可导出且可 JSON 序列化（前提已满足）；`gen:api` 脚本已就位，但**未实际运行** `openapi-typescript`（未 `npm install`） |
| 只引用 Fake provider | ✅ | `infrastructure/providers` 仅实现 fake；配置真实 provider 时**拒绝启动** |

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

## 5. known risks

| # | 风险 | 等级 | 现状 / 缓解 |
|---|---|---|---|
| R1 | **跨进程 checkpoint 恢复未演练** | 中 | B1 只验证了同进程 resume 语义；`langgraph-checkpoint-postgres` 未安装。B2 必须补：安装 → 起独立 checkpoint 库 → 中断进程 → 重启恢复。**在此之前不得声称"断点可跨进程恢复"** |
| R2 | **图逻辑未跑在真实 `StateGraph` 上** | 中 | 解释器与 `build_planning_graph` 的转移逐条对应，但框架的 reducer 语义（`operator.add`）与解释器的 merge 有一处**刻意的差异**：解释器在 repair 后显式清空 `validation_errors`（见 `graphs.py` 注释）。装框架后需重新验证该处行为一致 |
| R3 | **TS client 未实际生成** | 低 | `gen:api` 已就位；需 `npm install` 后跑一次并把生成物入库 |
| R4 | **新迁移基线未在真实 Postgres 上跑过** | 中 | SQL 未经执行验证（B0/B1 禁止连库）。B2 首要任务：在 `studyplan_test_*` 临时库执行 `alembic upgrade head` 并跑 RLS 断言 |
| R5 | **`ai_run_events` / `ai_provider_attempts` 无归属策略** | 低 | 已 `ENABLE ROW LEVEL SECURITY` 但未建 policy，B2 补（迁移注释已标注） |
| R6 | **前端未构建验证** | 低 | 未 `npm install`，未跑 `vite build` |
| R7 | **真实模型 provider 存在性仍 unverified** | 中 | 沿用 B0 结论；B3 处理 |
| R8 | 6–12 位密码上限低于常见建议 | 低 | 用户既定约束；已用 Argon2id 高成本参数 + 限流要求补偿（ADR-0006 记录取舍） |

---

## 6. next B1 input（进入 B2 的输入）

**B2 目标**：知识与计划业务域 —— 知识节点/关系/单元、路径草案与发布、版本、进度、
实践任务与知识多对多、偏好/资源表、迁移与权限。

**B2 必须先做（承自 B1 的未完成项）**：

1. **在真实 Postgres 上跑通迁移**（R4）：
   - bootstrap 创建 3 个 role + 2 个 database；
   - 在 `studyplan_test_*` 执行 `alembic upgrade head`；
   - 补 `test_postgres_rls.py`：受限角色断言越权读返回 0 行。
2. **补齐 `ai_run_events` / `ai_provider_attempts` 的 RLS policy**（R5）。
3. **安装 langgraph 并在真实 `StateGraph` 上重跑 B1 的图测试**（R2）：
   ```bash
   .venv/Scripts/python -m pip install -e ".[agent]"
   .venv/Scripts/python -m pytest backend/tests/unit/test_graph_workflows.py
   ```
   若 reducer 行为与解释器不一致，**以框架行为为准并修正解释器**，同时更新 `graphs.py` 注释。
4. **Postgres Checkpointer 恢复演练**（R1）—— 这是 B1 验收条款中唯一未完成项：
   - 起 `studyplan_checkpoint` 库；
   - 用 Fake 图跑到 `interrupt`；
   - **杀掉进程**，重启后 `Command(resume=...)` 恢复；
   - 断言恢复后 Run 投影与草案投影一致。
5. **B2 业务表设计**：按设计 §3 补齐 `knowledge_nodes` / `knowledge_relations` /
   `learning_units` / `unit_node_links` / `plan_stages` / `plan_unit_links` /
   `plan_task_links` / `unit_progress` / `practice_*` / `preferences` / `resource_records`。
   建议独立为 `0002_business_domain.py`，**不要**改 `0001`。

**B2 的验收情景**（设计 §5）：使用固定示例数据完成
「创建 → 草案 → 确认 → 跳过 → 重新规划 → 进度保留」，
且**同一计划草案重复确认不能重建两份**、**编辑必须重新验证**。

**B2 明确不做**：真实模型（B3）、完整 RAG（独立项目）、UI（B6）、图谱、长期记忆。

---

## 7. rollback

如需回退 B1：

```bash
cd D:/studyplan
rm -rf backend/app/ports backend/app/agent_workflows backend/app/infrastructure
rm -rf backend/app/domain/practice backend/tests backend/alembic backend/alembic.ini
rm -rf contracts scripts frontend/src frontend/*.json frontend/*.ts frontend/index.html
rm -f pyproject.toml
```

**回退不需要触碰 E 盘**：本批次未向 E 盘写入任何内容，
且 `docs/migration/source-provenance.md` 已证明无文件来自 E 盘复制。
B0 交付物（`docs/migration/`、`docs/adr/`）可独立保留。

> ⚠️ B1 结束时 `D:\studyplan` 尚无 commit。回退前建议先 `git add -A && git commit`
> 建立基线，使回退可用 `git revert` 而非删除文件。
