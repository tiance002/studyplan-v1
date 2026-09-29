# studyplan — 学习规划助手 V1.1

> 面向「想学 Agent 开发 / 云服务等可落地工程领域，并希望用 AI 编码工具做出真实项目」的用户：
> 从零生成完整知识体系 → 路径草案 → 用户确认 → 单元资料 → 自主总结 → AI 引导反馈 →
> 阶段实践任务 → 用户写实现思路 → AI 评审 → 导出 Prompt → 外部实现 → 证据验收 → 进入下一阶段。

**当前状态：B2-V 发布闭环、B3 模型设置及 B3-F1 正式前端已实现。**
可操作链路：注册 / 登录 → 学习目标 → 生成草案 → 编辑 / 确认 → 正式学习路径 → 阶段工作区。认证、计划、知识目录及进度读取使用真实 PostgreSQL；React 前端以 V6.3 为视觉基线。

本轮验收使用明确标识的 Fake LLM 预设 Agent 场景，不代表任意领域规划质量，也没有新增云模型验收。已有 OpenAI 兼容模型与加密个人配置仍可使用。会话、总结写入、评审及实践提交尚未开放。

- 基线与保全记录：`docs/reviews/B3-F1-baseline.md`
- 启动配置：`docs/development/B3-F1-startup.md`
- 验收证据及延期项：`docs/acceptance/B3-F1-report.md`
- 开发版本边界：`docs/development/B3-F1-scope.md`

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

已有本地数据库与 `.env` 时，先安装依赖并运行增量迁移，再分别启动后端和前端：

```powershell
.venv/Scripts/python -m pip install -e ".[dev,agent,postgres]"
npm --prefix frontend ci
./scripts/b3f1-dev.ps1 -Migrate
# 两个终端分别执行
./scripts/b3f1-dev.ps1 -Demo
./scripts/b3f1-dev.ps1 -Frontend
```

打开 `http://127.0.0.1:5173`，点击开放注册。用户名支持中文，密码 6–12 个 Unicode 码点，无邀请码。注册自动创建服务端归属学习空间；无需输入 actor、project 或访问令牌。

Demo 仅对启动进程设置 Fake LLM，不修改 `.env` 云模型凭据。使用已有真实模型配置时启动 `./scripts/b3f1-dev.ps1`，前端模型设置仍有效；模型调用可能产生服务商费用。

新环境的 PostgreSQL 角色、独立业务/Checkpoint 数据库与环境变量配置见 `docs/development/B3-F1-startup.md`。应用角色无 DDL；迁移角色与应用角色必须分离。未配置 PG 时仅能访问健康检查和接口文档，不能伪造成功业务结果。

```powershell
.venv/Scripts/python -m pytest -o addopts= -q -rs
.venv/Scripts/python -m ruff check backend
.venv/Scripts/python -m mypy backend/app
npm --prefix frontend test
npm --prefix frontend run build
node scripts/b3f1-browser.cjs
```

浏览器脚本需要运行中的两端服务和本机 Chrome；自动注册独立验收用户，截图写入 `output/playwright/`。后端 PG 测试只使用 `studyplan_test_*` 临时库，无可用安全 PG 时显式 SKIP。最终结果见验收报告。

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

## B3 模型能力

已有 OpenAI 兼容 `/chat/completions`、实际 StateGraph、独立 PG Checkpointer 与 Python 工程入门领域包。规划 POST 现在只把任务原子写入现有 `ai_jobs` 并返回 HTTP 202；需在另一个终端显式启动单 Worker：

```powershell
# 本地 .env 需显式配置 PLANNING_WORKER_ACTOR_IDS=user-id-1,user-id-2
./scripts/b3f1-dev.ps1 -Worker
```

**部署限制：** `PLANNING_WORKER_ACTOR_IDS` 白名单仅供本地开发与安全验证。当前开放注册会让新用户在未登记时无法生成计划；此机制不能作为云端公开 V1。开放上线前必须补齐无需逐用户手动登记、同时保持 RLS 隔离的安全领取方式，并通过伪造项目与跨用户并发验收。Worker 启动器会拒绝非开发环境，未配置的用户也会在入队时收到清晰错误。

运行异常进入 failed；超过配置预算仍未完成的运行在下一次读取时进入待核对，不自动再次调用模型。

个人 Base URL、模型名称和 API Key 由服务端按当前用户隔离保存；密钥加密且 GET 不回显。须通过部署 secret 提供稳定的 Fernet `MODEL_SETTINGS_ENCRYPTION_KEY`，并用 `LLM_ALLOWED_HOSTS` 管理允许的服务商。当前不支持 Anthropic `/messages` 协议。真实模型历史证据见 `docs/acceptance/B3-minimal-report.md`；本轮未运行付费云模型验证。

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
