# B0 模块复用矩阵：module-reuse-matrix

> 产出日期：2026-09-27 · 对应 `SOFTWARE_DESIGN.md` §2「复用与迁移策略」· 附 `IMPLEMENTATION_PLAN.md` §2
> **来源基线**：`LEGACY_ROOT = E:\codex_workspace\study-plan`，`HEAD = 1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1`（分支 `codex/v2-clean-baseline-20260925`，工作树 clean）。
> **判定标签**：`copy`（原样复制）· `adapt`（改造后迁入）· `reference-only`（只看不迁）· `drop`（不迁）。
> **铁律**：不迁 `.git/`、`.venv/`、`__pycache__/`、`node_modules/`、`.env*`、`var/`、本地数据库、checkpoint、上传文件、旧密钥。

---

## 0. 前置结论

`D:\studyplan` 在本次 B0 前**已有独立自研骨架**（core 624 行 + domain 1,863 行，见 `legacy-inventory.md` §6），且已验证可独立导入、不引用 E 盘。因此本矩阵的定位是：

1. **对已有骨架**：判定其与设计文档的一致性，指出缺口；
2. **对旧仓库**：判定「还有什么值得迁」，**默认拒绝**，只对极少数经过论证的模块放行。

> **总方针（对应验收条款「拒绝全仓库复制与重复构建执行引擎」）**：
> **本批次不迁入任何旧源码文件。** 全部旧能力判定为 `reference-only` 或 `drop`。理由见每行的「不迁原因」。

---

## 1. 主矩阵

### 1.1 基础设施与身份

| 旧模块 | 源路径 | 新版判定 | 依赖闭包 | 许可证 | 测试证据 | 依据 / 不迁原因 |
|---|---|---|---|---|---|---|
| ID 生成 | `backend/app/core/ids.py` (26 行) | **reference-only** | 无（标准库） | 项目内部 | 无独立测试 | 新版 `D:\studyplan\backend\app\core\ids.py` 已自研实现（`new_id` / `content_hash` / `slugify_stable_key` / `require_stable_key`），**实测可用**（`new_id('t')` → `t_5b28…`）。旧实现更单薄，无迁入价值。 |
| 哈希 | `core/hashing.py` (76 行) | **reference-only** | 无 | 项目内部 | 无 | 新版等价能力已并入 `core/ids.py::content_hash`；旧版额外做了内容寻址，V1 未用到。 |
| 错误模型 | `core/errors.py` (217 行) | **reference-only** | `core/ids` | 项目内部 | `test_error_payload_contract.py` | 新版 `core/errors.py`(119 行) 已自研：`ErrorCode` 12 值 + `STATUS_BY_CODE` 统一映射 + `AppError` 家族，**实测导入通过**。旧版 217 行含旧业务专属错误码，迁入会带入旧领域词汇。 |
| 请求上下文 | `core/request_context.py` (44 行) | **reference-only** | 无 | 项目内部 | `test_idempotency_and_tracing.py` | 新版已自研等价物；`request_id` 契约（设计 §9 最小日志字段）由新版 `core` 保证。 |
| 时钟 | `core/clock.py` (74 行) | **reference-only** | 无 | 项目内部 | 无 | 新版直接使用 `datetime.now(timezone.utc)`；V1 无注入可测时钟需求。 |
| 权限校验 | `core/authority.py` (40 行) | **reference-only** | — | 项目内部 | — | 新版把授权收进 `domain/workspace/models.py::AuthContext.require_project()`，**由服务端生成、禁止前端传入**（设计 §7 硬约束）。旧 authority 服务于旧 tenancy，语义不同。 |
| **口令与用户名** | `identity/passwords.py` (160 行) | **reference-only** ⭐ | `argon2-cffi` | MIT / Apache-2.0 / CC0 | `test_password_accounts.py`、`test_auth_hardening.py` | **本项是全仓库最有价值的资产**：单一策略入口 + Argon2id(19MiB,t=2,p=1) + 常数时间 dummy hash 防枚举 + 中文用户名 NFKC/casefold + 孤立代理项拒收。**但**新版 `CredentialPolicy` 已覆盖产品约束，且旧模块依赖旧 `models.Principal` 链。**判定：不迁代码，将其安全设计要点写成 B1 的验收条目**（见 §3）。 |
| 会话签发/校验 | `identity/session.py` (208 行) | **reference-only** | `core.clock`, `core.errors` | 项目内部 | `test_auth_hardening.py` | 旧用 **Bearer token**（`Authorization: Bearer`）；新版设计 §7 要求**签名 Cookie + CSRF/Origin**。传输载体不同，迁入需连同 `cookie_auth.py` 一并重构，收益低于重写。 |
| Cookie 认证 | `identity/cookie_auth.py` (180 行) | **reference-only** | 同上 | 项目内部 | `test_auth_hardening.py` | 同上。**新版 B1 应重新实现**，并把旧实现作为对照（特别是 CSRF / Origin / SameSite 的处理方式）。 |
| 限流 | `identity/rate_limit.py` (128 行) | **reference-only** | `db.rate_limit_store` | 项目内部 | `test_auth_hardening.py` | **设计 §"密码仍须使用安全散列、限流和合理存储"明确要求限流**。旧实现绑定旧 DB store；新版 B1 需自研（内存 + Postgres 两实现），旧版作参考。 |
| 幂等 | `identity/idempotency.py` (313 行) | **reference-only** | `db.idempotency_store` | 项目内部 | `test_http_idempotency.py` | 新版 `core/idempotency.py` 已有自研骨架。旧版 313 行含「同键同体返同结果 / 同键异体 409」完整实现，**B1 补 `IdempotencyConflictError` 语义时以此为对照**。 |
| 成员关系 | `identity/membership.py` (156 行) | **reference-only** | `identity.ports` | 项目内部 | `test_identity_repositories.py` | 新版 `domain/workspace/models.py::Membership` 已实现（owner/editor/viewer）。 |
| 租户上下文 | `tenancy/context.py` (156 行包) | **drop** | — | 项目内部 | `test_pg_isolation.py` | 新版用 `AuthContext.learning_project_scope` 表达项目归属；独立 tenancy 包与设计「workspace 域负责身份引用与项目授权」重复。 |
| 安全网关 | `policy/{gateway,taint,token}.py` (678 行) | **drop** | 自定义 | 项目内部 | 部分 | 服务于旧「教学结论门」。设计 §2 明确**不复用**该模式作为所有规划任务的门。其中 SSRF/XSS 防护要求已由新版 `domain/resources/models.py::require_safe_url` 独立实现（**实测拒绝 `127.0.0.1`**）。 |

### 1.2 业务域

| 旧模块 | 源路径 | 新版判定 | 依据 / 不迁原因 |
|---|---|---|---|
| 产品域（项目/会话/计划版本/任务） | `product/` (5 文件) | **reference-only** | 旧用任务 `title` 承载多字段；设计 §2 明确「不要靠旧任务 title 承载全部字段」。新版拆为 `catalog`/`planning`/`practice` 三个域，已有 `planning/models.py` 自研实现（`PlanDraft`/`PlanRevision`/`PlanStage`/`PlanUnitLink`/`PlanTaskLink` + `PlanPublicationService` + `diff_revisions` 按 `stable_key` 精确匹配）。 |
| 学习域（提交/证据） | `learning/` (8 文件) | **reference-only** | 「历史不可变提交」思路保留 → 新版 `reflections/models.py` 已实现（`SummaryAttempt` 不可变 + `attempt_no` 单调 + 同内容拒绝重提 + `attach_review` 幂等）。V1 **不使用旧掌握度打分**决定学习进度。 |
| 教学域（provider/attempt/budget） | `teaching/` (14 文件) | **reference-only** | 唯一保留价值：`providers_factory.py` 的「**凭据缺失即拒绝启动，绝不静默退回模拟器**」与 `openai_provider.py` 的「**适配器不自动重试**」两条原则，**写入 B1 的 `LLMPort` 契约**。旧代码本身绑定旧 `TeachingProvider` 形状，与新 `LLMPort.generate_structured(*, purpose, payload, schema_name, run_id, attempt_id)` 不同。 |
| 知识域（解析/检索/索引） | `knowledge/` (20 文件 / 5,190 行) | **drop** ⭐ | 设计 §2 §6 明确：索引引擎**交由独立 RAG 项目**维护，主项目只保留资源 URL 元数据/来源引用 + `RAGPort`。整包不迁，**避免在主服务里长第二套索引引擎**。 |
| 审计域 | `audit/{outbox,sink}.py` | **reference-only** | outbox 模式对 `ai_run_events` 有参考价值；但新版事件写入由 `ai_runs` 投影 + 领域事务承担，结构不同。 |
| 预算域 | `budget/` (4 文件) | **drop** | V1 范围不含平台预算治理（设计 §6「高并发调优、多层记忆/模型路由」列入可后延）。旧 `platform_budget_config` 种子行是旧库专属。 |
| 注册表 | `registry/` (3 文件) | **drop** | 旧 `workflow/catalog` 体系的一部分，随编排层替换一并废弃。 |
| 执行引擎 | `execution/` (5 文件 / 703 行) | **reference-only** ⭐ | 旧 `state_machine` + `confirmation` + `outbox` + `child_run` 的**租约/围栏/确认/对账语义**与新版 `ai_runs` 生命周期同构，是 B1 队列设计的**最佳参考**。但见 §1.3，**代码不迁**。 |
| 工作流 runtime | `workflow/runtime.py` (840 行) | **drop** ⭐ | **本项是最重要的 `drop`**：设计 §2 要求「LangGraph 是新业务编排唯一入口；**不能同时有两个争夺业务状态的工作流引擎**」。搬迁旧 runtime 会直接违反该约束。 |
| Worker | `workers/{acquisition,ingestion,teaching}.py` | **drop** | 绑定旧 knowledge/teaching 域；新版 worker 由 B1 用 `ai_jobs` 队列 + LangGraph 重建。 |
| API 路由 | `api/*_routes.py` (9 文件) | **drop** | 旧路由无 `/api/v1` 前缀且语义与新设计冲突（设计 §7「不要同时暴露两套含义不同的 `/plan/generate`」）。 |
| DB stores | `db/*_store.py` (18 文件) | **reference-only** | 「仓储按状态过滤」这一条对 `PlanRepositoryPort` 很关键（旧实现里 `save_draft` 会按状态过滤，避免取消的草案被 worker 发布）；新版 `planning/models.py` 已在 docstring 里记下该约束，B1 的 PG 实现须落实。 |

### 1.3 前端

| 旧模块 | 源路径 | 新版判定 | 依据 |
|---|---|---|---|
| 单页 HTML + vendor | `frontend/{index.html,app.js,views.js,commands.js,project-state.js,terms.js,api-client.js,app.css,vendor/}` | **reference-only** ⭐ | 实测：`frontend/src` 下 `.ts/.tsx` = **0 个**；无 vite / typescript / build script；React 通过 `vendor/*.min.js` 引入。与设计 §3「React + TypeScript + Vite + OpenAPI typed client」完全不同代际。**只参考旧交互行为与中文文案**（尤其 `terms.js` 的领域词汇表），**不迁代码**。 |
| vendor 许可证 | `frontend/vendor/*.LICENSE.txt` | **reference-only** | 若未来引入 antd/dayjs，须随附许可证。 |

---

## 2. 依赖闭包

### 2.1 本次实际迁入的依赖闭包

**空集。** 本批次未从 E 盘迁入任何源码文件，故无新增依赖闭包。

### 2.2 新版自身依赖（`D:\studyplan` 现状）

`D:\studyplan` 当前**尚无 `pyproject.toml`**（`backend/` 下只有 `app/`、`alembic/`、`tests/` 三个目录）。B1 需新建，建议基线：

| 依赖 | 版本下限 | 许可证 | 用途 |
|---|---|---|---|
| `fastapi` | >=0.115 | MIT | HTTP 接入 |
| `pydantic` | >=2.9 | MIT | DTO / 契约真相源 |
| `uvicorn` | >=0.32 | BSD-3 | ASGI server |
| `argon2-cffi` | >=23.1 | MIT / Apache-2.0 / CC0 | 口令散列（**设计强制要求安全散列**） |
| `PyYAML` | >=6.0 | MIT | 配置 |
| `psycopg[binary]` | >=3.2 | **LGPL-3.0-only** ⚠️ | Postgres 驱动；**须沿用豁免记录与许可证随附义务** |
| `alembic` | >=1.13 | MIT | 迁移 |
| `SQLAlchemy` | >=2.0 | MIT | ORM（若采用） |
| `langgraph` | 待定（B1 按锁定版本） | MIT | 编排层 —— **新增，旧仓库未用** |
| `langgraph-checkpoint-postgres` | 待定 | MIT | Postgres Checkpointer —— **新增** |
| dev: `pytest` / `httpx` / `ruff` / `mypy` | — | MIT | 门禁 |

> ⚠️ **LangGraph 是全新引入**：旧仓库**完全没有** LangGraph 依赖（旧用自研 `workflow/runtime.py`）。因此**不存在"旧 agent_workflows 可迁"这回事** —— 新版 `agent_workflows/` 必须从零构建。

---

## 3. 从旧代码提炼的 B1 验收条目（不迁代码，迁约束）

以下各条**不是复制代码**，而是把旧仓库用测试固化过的硬约束，转写成新版必须满足的验收项：

| # | 约束 | 旧证据 | 新版落地位置 |
|---|---|---|---|
| C1 | 口令恰好 6–12 **码点**，不 strip / 不截断 / 不大小写 / 不 NFKC；含孤立代理项必须 `ValueError` 而非 500 | `test_password_accounts.py` | `domain/workspace/models.py::CredentialPolicy` + 新测试 |
| C2 | 注册与登录**共用同一策略入口**，禁止双分支（否则"注册能设、登录被拒"） | `passwords.py` docstring 明写该事故 | 同上 |
| C3 | 未知用户也执行一次等价 Argon2 工作（`DUMMY_PASSWORD_HASH`），防用户名枚举 | `passwords.py` | `identity` 服务层 |
| C4 | 认证失败**不区分原因**（格式/签名/过期同一种错误） | `auth.py::BearerSessionAuthProvider` | `AuthContext` 生成器 |
| C5 | `AuthContext` **只能**由服务端从可信会话产生，任何地方不得从请求字段拼装 | `auth.py` docstring「唯一入口」 | `api/v1` 依赖注入 |
| C6 | 仓储查询必须带 scope；**取消的草案不得被 worker 稍后发布**（按状态过滤） | `db/*_store.py` | `PlanRepositoryPort` PG 实现 |
| C7 | Provider 凭据缺失时**拒绝启动**，绝不静默退回模拟器 | `providers_factory.py` | `infrastructure/providers` |
| C8 | 付费适配器**不自动重试**；未落库结果不得盲重发 | `openai_provider.py` | `LLMPort` 实现 + `ai_provider_attempts` |
| C9 | 迁移**不建 role、不建 extension**；角色缺失显式失败；downgrade 有业务数据时拒绝 | `0001_initial_schema.py` | 新版迁移基线 |
| C10 | `alembic.ini` 保持**纯 ASCII**（中文 Windows GBK 下 UTF-8 注释会让 alembic 在自身 Python 运行前就 UnicodeDecodeError） | `alembic.ini` 头部注释 | 新版 `alembic.ini` |
| C11 | 迁移角色与应用角色**强制分离**（迁移需 DDL，`study_app` 不得有 DDL） | `alembic.ini` 注释 | `.env.example` + bootstrap |
| C12 | 断言无环：前置依赖图必须无环 | `test_plan_quality.py`(旧) | `domain/catalog` + 测试 |

---

## 4. 明确拒绝的迁入项（对照验收条款）

| 被拒项 | 拒绝理由 |
|---|---|
| 全仓库复制 | 验收条款明文禁止；且 29,902 行中约 5,190 行（knowledge）+ 840 行（workflow runtime）属设计明确要求不复用的部分 |
| 重复构建执行引擎 | 迁 `workflow/runtime.py` 会形成「LangGraph + 自研 runtime」双引擎，违反设计 §2 |
| 旧 `.git` | 新项目独立 Git 历史（设计 §0） |
| 旧 `.venv` / `node_modules` | 环境隔离 |
| 旧迁移 `0001` revision id | 旧 0001 为旧业务域而建，新库需自建基线（设计 §2） |
| 旧邀请码链路 | 用户既定「无邀请码」，且已在旧仓库末版删除（`legacy-inventory.md` §4.1） |
| 旧数据库 / checkpoint / var / 上传资料 | 任务书明文禁止 |
| 旧前端代码 | 代际不匹配（CDN 单页 → Vite/TS） |
| 旧 `knowledge/` 索引引擎 | 应由独立 RAG 项目维护（设计 §2 §6） |

---

## 5. 复用结论一句话

> **B0 的选择性复用结论是：从旧仓库迁入「0 个源码文件」，迁入「12 条经测试固化的硬约束」（§3）。**
> 新版骨架的价值不在"搬了多少旧代码"，而在"是否守住了旧仓库用测试换来的那些约束"。这与验收条款「决定 B1 要选择性迁入哪些模块，拒绝全仓库复制与重复构建执行引擎」一致 —— 最安全的选择性复用，是识别出**当前没有值得迁入的模块**，并把结论写清楚。
