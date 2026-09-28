# studyplan — 学习规划助手 V1.1

> 面向「想学 Agent 开发 / 云服务等可落地工程领域，并希望用 AI 编码工具做出真实项目」的用户：
> 从零生成完整知识体系 → 路径草案 → 用户确认 → 单元资料 → 自主总结 → AI 引导反馈 →
> 阶段实践任务 → 用户写实现思路 → AI 评审 → 导出 Prompt → 外部实现 → 证据验收 → 进入下一阶段。

**当前状态：B0 完成 + B1 骨架就绪。**
本仓库交付的是**可运行的架构骨架 + 冻结的领域契约 + 三张 LangGraph 小图的可测试逻辑**，
不是一套已打通真实云模型、真实资源池的完整产品。完成度以 `docs/` 下的里程碑文档为准。

- **B0（已完成）**：本机新旧工程审计、复用清单、来源溯源、架构决策记录 →
  `docs/migration/`、`docs/adr/`
- **B1（骨架已就绪）**：领域契约、三张小图逻辑、队列/迁移基线、`/api/v1` 骨架、可独立测试
- **B2–B6**：见 `docs/design-package/IMPLEMENTATION_PLAN.md` §5

---

## 1. 这个仓库是什么

| 层 | 技术 | 职责 |
|---|---|---|
| 前端 | React 19 + TypeScript + Vite | 仅消费 OpenAPI 生成的 typed client，不自造业务状态、不自报身份 |
| 接入 | FastAPI + Pydantic | `/api/v1` HTTP 层，`AuthContext` 由服务端会话生成 |
| 应用 | application use cases | 跨领域事务协调，一个命令一个可辨识事务边界 |
| 领域 | domain（纯 Python） | 六个限界上下文：workspace / catalog / planning / resources / reflections / practice |
| 端口 | ports（Protocol） | LLM / Resource / RAG / GraphRunner / Repository |
| 工作流 | LangGraph StateGraph | 三张小图：规划、总结评审、Prompt 评审 |
| 基础设施 | Postgres / worker / providers | 业务库 + 独立 checkpoint 库、租约队列、真实/外部适配器 |

严格依赖方向：`api -> application -> domain & ports <- infrastructure`。
`domain` **不得** import FastAPI、LangGraph、ORM 或任何 SDK —— 这条由
`backend/tests/unit/test_import_direction.py` **机械保证**，不靠评审记忆。

## 2. 三个权威状态源（不要混用）

| 状态 | 存放地 | 说明 |
|---|---|---|
| 业务事实 | `studyplan_app` 领域表 | 进度、计划版本、总结、任务、成果；**唯一真相** |
| 图断点 | `studyplan_checkpoint`（独立库/角色） | 只保存工作流执行位置，不是业务状态 |
| 对外运行态 | `ai_runs` 投影 | 可授权的 RunView，浏览器只看这个 |

## 3. 快速开始

### 3.1 跑测试（不需要 Postgres / 网络 / langgraph）

```bash
bash scripts/test.sh
# 或手动：
python -m venv .venv
.venv/Scripts/python -m pip install pytest fastapi httpx
.venv/Scripts/python -m pytest
```

预期：**104 passed**（unit + contract + integration；Postgres 组自动跳过）。

### 3.2 启动 API（骨架模式，内存仓储 + Fake 模型）

```bash
bash scripts/dev.sh
# 或手动：
cd backend
LLM_PROVIDER=fake STUDYPLAN_REPOSITORY_BACKEND=memory ../.venv/Scripts/python -m uvicorn app.main:app --port 8000
```

打开 http://127.0.0.1:8000/docs 查看 OpenAPI（骨架阶段仅有 `/healthz`，
业务路由属 B2）。

### 3.3 切换到真实 PostgreSQL（B2 起可用）

```bash
cp .env.example .env      # 填写三个 DSN（业务库 / checkpoint 库 / 迁移 DSN）
cd backend
../.venv/Scripts/python -m pip install -e ".[postgres]"
STUDYPLAN_MIGRATION_DSN=... ../.venv/Scripts/python -m alembic upgrade head
```

⚠️ 迁移角色与应用角色**必须不同**（`studyplan_app` 无 DDL），见 `docs/adr/ADR-0003`。

### 3.4 前端

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173，/api 代理到 127.0.0.1:8000
```

## 4. 三张图

```
planning_graph
  START -> normalize -> generate_outline -> build_dependencies_and_units
        -> propose_practice -> validate -> [repair <= 2] -> save_draft_projection
        -> await_approval(interrupt) -> (cancel | edit+validate | approve)
        -> commit_plan_idempotently -> END

summary_review_graph     START -> load_rubric_snapshot -> review_once -> validate_review -> persist_review_idempotently -> END
prompt_review_graph      START -> load_task_from_revision -> review_once -> validate_review -> persist_review_idempotently -> END
```

只有 `planning_graph` 可暂停等待用户。总结与 Prompt 的每次修订 = 新的 `attempt/revision + run`，
**不会**让图挂起数月。普通 CRUD 与状态机使用应用服务，不包 Graph。

> **B1 说明**：图逻辑由 `app/agent_workflows/graphs.py` 的确定性解释器实现并测试；
> 安装 `langgraph`（`pip install -e ".[agent]"`）后可切换为真实 `StateGraph`。
> 这一顺序是刻意的 —— 图的**转移逻辑**（修复上限、interrupt 位置、取消语义）
> 才是风险所在，把它写成可独立测试的纯函数风险最低。

## B3 本地最小闭环

当前支持 OpenAI 兼容 `/chat/completions`、实际 StateGraph 与独立 PG Checkpointer、Python 工程入门领域包和路线前端。同步生成完成后返回 HTTP 202；尚不是异步 worker。

在 `.env` 填写 `LLM_MODEL_ID`、`LLM_API_KEY`；`LLM_BASE_URL` 默认 `https://api.openai.com/v1`，可替换为服务商的兼容地址。密钥只放本机 `.env`。本机数据库已准备时不要重复运行安装脚本。

```powershell
# 两个终端分别运行
./scripts/b3-dev.ps1
./scripts/b3-dev.ps1 -Frontend
# 使用真实模型生成并确认一条验证路线（会产生模型费用，独立验证项目）
./scripts/b3-verify-live.ps1
```

打开 `http://127.0.0.1:5173`，使用 `.env` 的 `STUDYPLAN_LOCAL_SESSION_TOKEN` 进入本地学习空间。填写目标、生成、编辑并保存、确认或取消。模型结果未知时进入待对账，不自动重发。当前单用户会话不替代后续注册登录。

“模型设置”允许当前会话用户保存自己的 OpenAI 兼容 Base URL、模型名称和 API Key；密钥在服务端加密，不会在 GET 响应或页面刷新后回显。生成时固定个人配置修订，未配置个人模型时明确使用部署默认模型。部署时须通过 secret 提供稳定的 `MODEL_SETTINGS_ENCRYPTION_KEY`（Fernet 密钥），并用 `LLM_ALLOWED_HOSTS` 管理允许访问的兼容服务商主机；当前初始名单是 `api.openai.com,api.deepseek.com`。云端还需正式用户认证和阻断私网/metadata 的出口策略；仓库的本地单用户会话不能直接用于公开多用户部署。当前不支持 Anthropic `/messages` 协议。

新环境先安装依赖 `pip install -e ".[dev,agent,postgres]"`，准备本机 PG 的迁移/应用角色，复制 `.env.example` 并清空其中 `DATABASE_URL`，再运行 `.venv/Scripts/python scripts/b3-setup-local.py`。脚本只创建随机新库与 checkpoint 角色，已有配置会拒绝重复建库；生产安装应使用独立管理凭据执行迁移和播种。

验收范围及真实模型待验项见 `docs/acceptance/B3-minimal-report.md`。

## 5. 仓库结构

```
backend/app/api/v1/           HTTP DTO / routes / auth adapter（B2）
backend/app/application/      跨域用例、事务协调（B2）
backend/app/domain/{workspace,catalog,planning,resources,reflections,practice}/
backend/app/ports/            LLM / Resource / RAG / GraphRunner / Repository
backend/app/agent_workflows/  graph builders / state / nodes / validators
backend/app/infrastructure/   db / checkpointer / worker / providers / external
backend/app/core/             id / error / config / request_id / idempotency
backend/tests/{unit,contract,integration,e2e}
frontend/src/                 api(generated) / features / shared
contracts/                    openapi.json + examples
docs/                         design-package / adr / migration / acceptance
scripts/                      safe test / dev
var/ .venv/                   仅本机，不入库
```

## 6. 关键不变量（改代码前请先读）

- **跳过 ≠ 完成 ≠ 掌握**：`UnitProgress.skipped` 不赋予任何掌握标签。
- **只有用户确认的 `PlanRevision` 是当前路线**；草案不得覆盖正式路线；取消/失败不影响当前计划。
- **发布计划必须在一个事务内**完成：校验草案 hash + `expected_version` + 幂等键 → 新增 revision/links → 设置当前引用。
- **`run_id + operation_key` 唯一且可重放**：重复确认不能生成两份计划。
- **付费调用结果未知不自动重发**：进入 `reconciliation_required`，不盲目重试。
- **资源 HTTP 200 ≠ 内容质量**；找不到真实资源返回 `unavailable`，**绝不伪造 URL 或视频时间戳**。
- **不得自动 clone 并执行外部仓库代码**；外部网页内容视为不可信数据（防 SSRF / XSS）。
- **AI 生成的知识先为项目私有草稿**，验证后才共享；关系图必须无环。
- **AI 不能独立作出「验收通过」结论**：须由用户确认或系统核验证据。
- **`thread_id` 与 checkpoint 结构永不返回给前端**；前端只拿稳定 `next_action`。
- **错误体固定含** `code / message / request_id / details`，不回显敏感输入。
- **认证**：开放注册、中文用户名、6–12 位密码、**无邀请码**（见 `docs/adr/ADR-0006`）。

## 7. 文档索引

| 文档 | 内容 |
|---|---|
| `docs/design-package/SOFTWARE_DESIGN.md` | 软件架构与详细设计（V1.1-LG） |
| `docs/design-package/IMPLEMENTATION_PLAN.md` | 实施方案与 B0–B6 里程碑 |
| `docs/adr/` | 6 条已冻结架构决策（含被拒绝的备选方案） |
| `docs/migration/legacy-inventory.md` | B0 本机审计事实（旧 HEAD / dirty / 分支） |
| `docs/migration/module-reuse-matrix.md` | 逐模块 copy/adapt/reference-only/drop 判定 |
| `docs/migration/source-provenance.md` | 每个文件的 SHA-256 与来源 |
| `docs/acceptance/B1-report.md` | B1 验收：changed files / commands / results / risks |

## 8. 许可证

见 `LICENSE`（MIT）。
⚠️ 若引入 `psycopg`（LGPL-3.0-only），分发时须随附其许可证文本，
参见 `docs/migration/module-reuse-matrix.md` §2.2。
