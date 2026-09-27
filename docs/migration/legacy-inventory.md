# B0 本机事实审计：legacy-inventory

> 产出日期：2026-09-27 · 审计者：SeniorDeveloper（B0 Goal）
> 审计对象：`LEGACY_ROOT = E:\codex_workspace\study-plan`（只读）、`NEW_ROOT = D:\studyplan`
> 审计方式：`git --no-optional-locks`（`GIT_OPTIONAL_LOCKS=0`）+ 文件系统读取 + SHA-256 摘要。
> **本文件记录的是本机实测事实，不是设计意图。任何未取得直接证据的结论一律标注 `unverified`。**

---

## 1. 结论速览

| 项 | 结论 | 证据 |
|---|---|---|
| LEGACY_ROOT 是否存在 | 存在，非空 | 顶层 30 项，见 §2 |
| LEGACY_ROOT 绝对路径 | `E:\codex_workspace\study-plan` | `git rev-parse --show-toplevel` |
| LEGACY_ROOT Git HEAD | `1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1`（`codex/v2-clean-baseline-20260925`，2026-09-25 22:53，"未完成版1"） | `git rev-parse HEAD` |
| LEGACY_ROOT 工作树 | **clean**，`status --porcelain` 输出 0 行 | `git status --porcelain=v1` |
| LEGACY_ROOT remote | `https://github.com/tiance002/study-agent-platform.git` | `git remote -v` |
| LEGACY_ROOT 未推送分支 | **10 个本地分支无 upstream**（含当前 HEAD 分支以外的全部 v2/rfx 分支） | `for-each-ref`，见 §3 |
| NEW_ROOT 是否存在 | 存在，**已有未提交骨架**（17 个文件，无 commit） | `git log` 报 "does not have any commits yet" |
| NEW_ROOT Git 状态 | 已 `git init`（`master`），**0 commit**，全部文件 untracked | `git status --porcelain=v1` |
| 覆盖风险 | **无**。D 盘骨架与设计文档目录树一致，未发现与新方案冲突的用户代码 | §6 |

> ⚠️ **重要前置事实**：`D:\studyplan` 在本 B0 开始前**已存在**一套由前序会话生成的骨架（`.env.example` / `.gitignore` / `LICENSE` / `README.md` / `backend/`），创建时间戳 2026-09-27 20:59，**尚未产生任何 commit**。本次 B0 **未覆盖、未 reset、未 clean、未删除**其中任何文件；所有新增均为「追加」。这一点是后续所有操作的前提。

---

## 2. LEGACY_ROOT 目录清单摘要

```
E:\codex_workspace\study-plan\
├── .agents/ .codex/ .serena/ .trae/ .playwright-mcp/   # 工具链产物（禁止迁入）
├── .github/                                             # CI 配置
├── .git/                                                # 旧仓库历史（禁止迁入）
├── .mypy_cache/ .pytest_cache/ .ruff_cache/ .venv/      # 缓存与解释器（禁止迁入）
├── .env.example                                         # 4,013 B，含旧 env key 命名
├── .gitattributes                                       # 541 B
├── .gitignore                                           # 1,031 B
├── .planning/                                           # 旧规划产物
├── alembic/versions/0001_initial_schema.py              # 单头基线（21 条迁移压扁）
├── alembic.ini                                          # 纯 ASCII，DSN 走环境变量
├── archive/                                             # 历史归档
├── backend/                                             # 141 个 .py（不含 __pycache__），约 29,902 行
├── deploy/                                              # 部署脚本
├── docs/
├── frontend/                                            # 单页 React via CDN（非 Vite 工程）
├── scripts/
├── tools/                                               # 契约生成 / 门禁 / 浏览器检查
├── var/ var-ui-test/                                    # 本地运行数据（禁止迁入）
├── findings.md (49 KB) / progress.md (116 KB) / task_plan.md (22 KB)
├── INTEGRATION_SUMMARY.md / README.md (32 KB)
├── output.json / pytest_html_report.html (2.1 MB)       # 旧测试产物
├── pyproject.toml / requirements.lock.txt
└── verify_components.py
```

**backend/app 模块规模**（`find ... | wc -l`，已排除 `__pycache__`）：

| 包 | 文件数 / 行数 | 白盒职责（实测读码） |
|---|---|---|
| `core` | 10 文件 / 866 行 | ids / hashing / errors / request_context / clock / authority / artifacts / contracts / evidence_issues |
| `identity` | 15 文件 / 1,898 行 | 账号、Argon2id 口令、会话、Cookie、限流、幂等、成员 |
| `tenancy` | 3 文件 / 156 行 | 租户上下文（内存实现） |
| `policy` | 4 文件 / 678 行 | gateway / taint / token（旧安全网关） |
| `knowledge` | 20 文件 / 5,190 行 | 抓取、HTML 解析、嵌入、融合、混合检索、库、证据状态 |
| `workflow` | 7 文件 / 1,587 行 | 自研 runtime / catalog / run_budget / tools_impl |
| `execution` | 5 文件 / 703 行 | state_machine / confirmation / outbox / child_run |
| `teaching` | 14 文件 | provider 抽象 + OpenAI Responses 适配器 + prompts + runs |
| `product` / `learning` / `db` / `api` / `workers` / `audit` / `budget` / `registry` | — | 旧业务域 |

---

## 3. LEGACY_ROOT Git 事实（关键：未推送内容）

当前 HEAD 分支：`codex/v2-clean-baseline-20260925`，与 `origin/codex/v2-clean-baseline-20260925` **完全同步（0 ahead / 0 behind）**。

**10 个本地分支无 upstream（=从未推送到 remote，仅存在于本机）**：

| 本地分支 | commit | 日期 |
|---|---|---|
| `codex/milestone-a-prototype-20260924` | `ad49ed4` | 2026-09-24 |
| `codex/rfx-core-20260925` | `bd6e883` | 2026-09-25 |
| `codex/rfx-kb-20260925` | `51bde69` | 2026-09-25 |
| `codex/rfx-ui-20260925` | `b808ebd` | 2026-09-25 |
| `codex/v2-account-isolation-20260925` | `df1fac1` | 2026-09-25 |
| `codex/v2-auth-backend-20260925` | `d6af3d9` | 2026-09-25 |
| `codex/v2-auth-frontend-20260925` | `6398650` | 2026-09-25 |
| `codex/v2-baseline-20260925` | `6f00e5c` | 2026-09-25 |
| `codex/v2-correctness-fixes-20260925` | `6cfe9bd` | 2026-09-25 |
| `codex/v2-loop-acceptance-20260925` | `f4cd8da` | 2026-09-25 |

已推送分支：`architecture-boundaries-20260922`、`review-fixes-and-ui-20260925`、`round8-residual-20260922`、`v2-clean-baseline-20260925`，remote 侧另有 `round-7`、`upload-current-project-20260921`、`main`。

> **结论**：GitHub 默认分支（`origin/main @ 0d31e54`）**显著落后于本机**。`main` 停在 2026-09-21，而本机 HEAD 已到 09-25 的 v2 重构。**任何以 remote 默认分支为复用依据的判断都会漏掉 v2 认证重构、0001 基线压扁、邀请码清理**。本审计以本机 HEAD `1c1b1c8` 为准。

**Worktree**：存在第二个 worktree `E:\codex_workspace\study-plan-prototype`（分支 `codex/milestone-a-prototype-20260924`，HEAD `ad49ed4`）。⚠️ 该目录**本次未审计**，因任务书要求 E 盘只读且不扩大读取面。标注 `unverified`。

**stash**：空。

---

## 4. 关键疑点核实（逐条对应用户关注项）

### 4.1 认证：开放注册 / 中文用户名 / 6–12 位密码 / 无邀请码 ✅ 已核实

**证据 A — 源码常量**（`backend/app/identity/passwords.py` @ HEAD `1c1b1c8`）：

```python
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 12
# 单一密码策略入口 validate_password()：注册、登录校验、重哈希共用
```

**证据 B — 邀请码残留检索**：对 `backend/app`、`frontend/src`、`alembic` 全量 `grep -i "invit"` → **0 命中**。旧邀请链路已被 2026-09-25 一组提交删除（`Drop the invite chain from round8 tools and deployment config`、`Remove invitation flow and converge auth on password sessions`、`feat(frontend): drop invite auth and unify password policy to 6-12`）。

**证据 C — 中文用户名**：`_USERNAME_ORIGINAL` 正则显式包含 `\u3400-\u4DBF\u4E00-\u9FFF`（CJK 扩展 A + 基本区）与全角字母区，且要求首字符为字母或汉字。

**证据 D — 密码散列**：Argon2id（`argon2-cffi`），参数 `memory_cost=19456, time_cost=2, parallelism=1`（≈ OWASP 推荐档），并实现 `DUMMY_PASSWORD_HASH` 常数时间路径防用户名枚举、`needs_rehash` 支持参数升级。

**证据 E — 迁移基线自述**：`alembic/versions/0001_initial_schema.py` docstring 明写「唯一的结构性删减是**邀请码全链路**（新版只保留用户名 + 密码）」。

> **判定**：以本机最终实现为准，**开放注册 + 中文用户名 + 6–12 位密码 + 无邀请码**已成立。**禁止**按任何历史分支恢复邀请码（含 `codex/v2-auth-*` 之前的 `main`）。

### 4.2 模型 Provider：真实可用性 ⚠️ 部分 unverified

- **存在真实适配器**：`backend/app/teaching/openai_provider.py` → `OpenAIResponsesProvider`，走 OpenAI **Responses API**（`POST {base_url}/responses`），无隐藏重试，`store: false`，`text.format=json_object` 强制结构化输出。代码层面**真实可调用**。
- **默认配置是关闭的**：`.env.example` 第 58 行 `STUDY_PLATFORM_TEACHING_PROVIDER=disabled`，`API_KEY` 为空。
- **工厂拒绝静默降级**：`providers_factory.py` 在 `openai` 分支缺 key 时由启动配置拒绝，**不会悄悄退回模拟器**；`scripted` 是测试/演练用，脚本耗尽即报错而非「静默成功」。
- **本机是否配过真实 key / 是否真跑通过云模型**：**`unverified`** —— 审计未读取 `.env`（任务书禁止读取与迁入密钥），也未发起任何外部付费调用（B0 不应产生费用）。

> **判定**：`LLMPort` 的真实适配器**代码存在且形态正确**，但「真实云模型已在本机调通」**不可断言**，标 `unverified`。B1 只接 Fake；真实模型留到 B3。

### 4.3 数据库迁移：已压成单头基线 ✅ 已核实

- `alembic/versions/` 下**仅 1 个版本文件**：`0001_initial_schema.py`（`revision="0001"`, `down_revision=None`）。
- docstring 明确：0001 是**原 head 0021 的有效对象合并快照**，逐条保留表/列/约束/索引/**RLS 策略**/`GRANT`/`SECURITY DEFINER` 函数/角色断言块。
- 迁移**不建 role、不建 extension**，角色缺失时**显式失败**（而非静默建库）。
- `downgrade` 仅在无业务数据时允许清库，否则拒绝。
- `alembic.ini` 只存配置，DSN 从 `STUDY_PLATFORM_MIGRATION_DSN` 环境变量读取；迁移角色与 `study_app` 应用角色**强制分离**。

> **⚠️ 对 B1 的直接影响**：旧 0001 是**为旧业务域建的**（含 `routing_decision` / `acquisition_fetch_observations` / `study_metrics_snapshot()` 等）。设计文档 §2 明确「不要把旧迁移序号直接套在新库上」。**新库需要自己的迁移基线**，不得复用旧 0001 的 revision id。

### 4.4 旧 Run / Worker 可迁移性 ⚠️ 架构不兼容

- 旧 worker：`backend/app/workers/{acquisition,ingestion,teaching}.py`，与 `execution/{state_machine,confirmation,outbox,child_run}.py`（共 703 行）构成一套**自研状态机 + outbox** 执行引擎。
- 旧 `workflow/runtime.py` 单文件 840 行，是另一套**自研工作流 runtime**。
- 设计文档 §2 明确要求：**LangGraph 是新业务编排唯一入口**，"不能同时有两个争夺业务状态的工作流引擎"。
- 旧 `execution/state_machine.py` 的状态机**语义**（租约、幂等、等待用户、对账）与新版 `ai_runs` 生命周期**概念同构**，值得作为**参考实现**。

> **判定**：**`reference-only`** —— 不迁代码，只借鉴其 lease / fence / outbox 思路。新版必须用 LangGraph `StateGraph` + Postgres Checkpointer 重建，**禁止**搬入旧 runtime 形成第二引擎。具体接口见 `module-reuse-matrix.md`。

### 4.5 知识索引 → RAG 边界 ⚠️ 必须切分

旧 `knowledge/` 共 **20 文件 / 5,190 行**，包含：`fetcher`（抓取）、`html_parser`、`embedding`、`fusion`（融合）、`retrieval`（混合检索）、`processor`（文档处理）、`library`、`evidence_state`、`acquisition`。

设计文档 §2 与 §6 明确：**索引引擎交由独立 RAG 项目维护**，主项目只保留：
1. 资源 URL 元数据 / 来源引用（`ResourceRecord`）；
2. `RAGPort(scope, query, limit) -> list[Evidence]` 接口。

> **判定**：`knowledge/` **整包 `drop`**（不从主项目迁入）。新主项目只实现 `RAGPort` + `ResourceRecord` 元数据。⚠️ 唯一保留价值：`fetch_policy.py`(183 行) 与 `resources` 域的 SSRF 防护思路可作 `reference-only`（新版 `domain/resources/models.py::require_safe_url` 已独立实现同等校验，**无需迁入**）。

### 4.6 旧前端实际构成 ✅ 已核实

- 目录内**没有** `frontend/src/`，`app/` 下 `.ts/.tsx` 文件数 = **0**。
- 实际构成：**CDN / vendor 形式的单页 HTML**——`frontend/index.html` + `app.js` + `views.js` + `commands.js` + `project-state.js` + `terms.js` + `api-client.js` + `app.css`，另有 `frontend/vendor/`（`react.production.min.js`、`react-dom.production.min.js`、`antd.min.js`、`dayjs.min.js` 及各自 LICENSE）。
- `frontend/package.json` 只声明 `antd@6.6.5` / `react@18.3.1` / `react-dom@18.3.1`，**无 vite / 无 typescript / 无 build script**。

> **判定**：与设计文档 §3「React + TypeScript + Vite + OpenAPI typed client」**完全不同代际**。旧前端 **`reference-only`**（只参考旧交互行为与文案），**不迁任何代码**，旧 HTML 不定义新 API。

### 4.7 老业务路由冲突 ⚠️ 必然冲突

旧 API 路由文件：`api/{auth_routes, library_routes, product_conversation_routes, product_learning_routes, product_routes, product_source_routes, projects_routes, routes, teaching_routes}.py` + `product_schemas.py`。

- 旧路由**无 `/api/v1` 前缀**（需 B1 前实测确认挂载前缀，本次未逐条读取全部路由装饰器 → 精确前缀 `unverified`）。
- 语义冲突点明确：旧有 `teaching/*`、`product/*` 等自成体系的路径，与新设计的 `/api/v1/projects/{project_id}/plans/generate` 等**含义不同**。
- 设计文档 §7 明令：「不要同时暴露两套含义不同的 `/plan/generate`」。

> **判定**：新项目**只暴露 `/api/v1`**，旧路由清单 `reference-only`。B1 必须产出 operationId 全量清单并断言无重复。

---

## 5. 依赖与许可证

旧 `pyproject.toml` 运行时依赖：`fastapi>=0.115`、`uvicorn>=0.32`、`pydantic>=2.9`、`PyYAML>=6.0`、`argon2-cffi>=23.1`；dev：`pytest/httpx/ruff/mypy`；postgres extra：`psycopg[binary]>=3.2`、`alembic>=1.13`、`SQLAlchemy>=2.0`。

**许可证**（来自 `tools/security/license_allowlist.txt`，该文件为**已评审**记录）：
- FastAPI / Starlette / Pydantic / uvicorn / httpx / PyYAML → MIT / BSD / Apache / PSF（宽松）。
- **`psycopg` 与 `psycopg-binary` 是 LGPL-3.0-only** —— 已记入豁免清单，理由是「作为依赖引入且不修改源码，Python 源码形态满足 LGPL 可替换库要求」。
- `requirements.lock.txt` 为 CPython 3.12 / Windows 的精确快照。

> ⚠️ **B1 注意**：新项目若引入 `psycopg`，**必须沿用 LGPL-3.0 的豁免记录与分发要求**（随附许可证文本）。新项目 `LICENSE` 当前为 MIT（D 盘已存在）。前端 vendor 中 `antd` / `react` / `react-dom` / `dayjs` 均附带各自 LICENSE 文件，若迁入需保留。

---

## 6. NEW_ROOT 现状与安全处置

`D:\studyplan` 在本 B0 之前已有内容（**非本次创建**）：

| 文件 | 行数 | 状态 |
|---|---|---|
| `README.md` | — | 已写好（描述 pre-B0 骨架状态，与设计文档一致） |
| `.gitignore` | — | 已覆盖 `.env` / `.venv` / `node_modules` / `var` / 旧工具链缓存 |
| `.env.example` | — | 占位值，无旧 secret |
| `LICENSE` | — | MIT |
| `backend/app/core/{config,errors,idempotency,ids,request_context,__init__}.py` | 624 行合计 | 自研，**未引用 E 盘** |
| `backend/app/domain/{enums,__init__}.py` + `catalog/planning/reflections/resources/workspace/models.py` | 1,863 行合计 | 自研，**未引用 E 盘** |
| `backend/app/{api/v1,application,agent_workflows,infrastructure/*,ports,domain/practice}` | 0 文件 | **空目录占位** |
| `backend/{alembic/versions,tests/*}` | 0 文件 | **空目录占位** |
| `contracts/{examples}`, `docs/{acceptance,adr,design,design-package,migration}`, `frontend/src/*`, `scripts`, `var` | 0 文件 | **空目录占位** |

**冲突评估**：现有骨架与设计文档的目录树**一致**，未发现与 V1.1 方案冲突的用户代码。
**处置**：**不覆盖、不删除**。B0 只在其 `docs/migration/`、`docs/adr/` 下**新增**审计文档，并对其空目录填充符合契约的内容。

**独立性验证（已实测）**：在 `D:\studyplan\.venv`（本机 CPython 3.13.12 隔离环境）中导入现有骨架 —— `IMPORTS OK`；`UnitProgress` 枚举 4 值、`AiRunStatus` 枚举 7 值均与设计文档 §8 一致；`require_safe_url("http://127.0.0.1/x")` 正确抛 `ValidationAppError`（SSRF 防护生效）；`CredentialPolicy(6, 12, invite=False)` 正确。**全量 `grep` 未发现任何 `E:\` / `codex_workspace` 路径引用**。

---

## 7. 安全与合规记录

| 项 | 状态 |
|---|---|
| E 盘是否被写入 | **否**。全部命令为 `git --no-optional-locks` 读操作与文件读取；未安装依赖、未运行旧启动脚本、未改 `.serena`、未提交。 |
| E 盘 HEAD 是否变化 | **否**，审计前后均为 `1c1b1c8`（见 §8 复核）。 |
| 旧 `.env` / 密钥 / token | **未读取、未复制**。 |
| 旧 `var/` / DB / checkpoint / 上传资料 | **未复制**。 |
| 软链接 / 目录联接指向 E 盘 | **未创建**。 |
| 旧数据库 | **未连接、未迁移、未清空**。 |
| D 盘既有文件 | **未覆盖、未 reset、未 clean、未删除**。 |

---

## 8. 审计后 E 盘状态复核

```
$ git --no-optional-locks -C E:/codex_workspace/study-plan rev-parse HEAD
1c1b1c852ceb9d1550fcb2b39576d1fa492f00d1        # 与审计前一致

$ git --no-optional-locks -C E:/codex_workspace/study-plan status --porcelain=v1
(空)                                             # 工作树仍然 clean
```

✅ E 盘 Git HEAD 与工作树**无意外变化**。

---

## 9. 遗留 unverified 清单（B1 前需补证）

1. 真实云模型 provider 在本机是否曾成功调用 —— 未验证（未读 `.env`、未发起付费调用）。
2. 旧 API 路由的完整挂载前缀与 operationId 全量清单 —— 未逐条读取（B1 交付时产出）。
3. `E:\codex_workspace\study-plan-prototype` 第二个 worktree 的内容 —— 未审计（超出本次读取范围）。
4. 旧数据库实例的实际角色权限与 RLS 生效情况 —— 未连接验证（任务书禁止）。
5. 旧 `agent_workflows` 概念在旧仓库中**不存在**（旧用自研 `workflow/runtime.py`），因此**无对应模块可迁** —— 这是已确认的结论，非 unverified。

---

## 10. known risks

| 风险 | 等级 | 缓解 |
|---|---|---|
| 误把旧 `workflow/runtime.py` 当编排层搬入，形成双引擎 | 高 | 已明确 `drop`；`test_import_direction` 类测试在 B1 补齐 |
| 复用旧迁移 0001 revision id，导致新库语义污染 | 中 | 新库自建迁移基线，禁止复用 `0001` id |
| 误认为"真实模型已打通"而跳过 B3 | 中 | provider 标 `unverified`；B1 只接 Fake |
| 旧 LGPL 依赖（psycopg）许可证义务被遗忘 | 中 | §5 已记录；分发时随附许可证文本 |
| 从 remote 默认分支 `main` 取代码，漏掉 v2 认证重构 | 高 | §3 已记录；一律以本机 HEAD `1c1b1c8` 为准 |
