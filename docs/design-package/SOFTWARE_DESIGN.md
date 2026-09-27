# 学习规划助手 V1.1：软件架构与详细设计

> LangGraph 正式作为工作流编排层；FastAPI 作为 HTTP 接入，PostgreSQL 作为业务事实源。版本 V1.1-LG / 2026-09-27。工程实际路径：只读旧 `E:\codex_workspace\study-plan`，新版 `D:\studyplan`。本文件描述预期实现而非声称已部署。

## 1. 总体架构、工程布局和导入方向

```text
React/TypeScript/Vite :5173  -- /api 同源代理 --> FastAPI :8000
                                                   |
         API DTO/OpenAPI/AuthContext/RunView        |
                      Application Use Cases --------+
       workspace / catalog / planning / resources / reflections / practice
                      |                |
                  Domain/Ports   GraphRunnerPort ---> agent_workflows [LangGraph]
                      |                |                    |
            PostgreSQL business       LLMPort / ResourcePort / GitHubPort / RAGPort
                      |                |                    |
              AiRun + job DB <---- worker -------- Infrastructure Adapters
                                     |
                       Postgres Checkpointer (独立 DB/Role)
```

严格依赖方向：`api -> application -> domain & ports <- infrastructure`。`agent_workflows` 只通过应用服务/Ports 读写业务实体，不能自行 SQL 并创造第二份业务规则。Domain 不得 import FastAPI、LangGraph、ORM、SDK；外部 RAG 不拥有学习进度。唯一业务事实源为领域表；Graph checkpoint 只保存工作流执行位置；`ai_runs` 是可授权的对外运行状态投影。

建议实际目录：
```text
D:\studyplan\
  backend\app\
    api\v1\                   HTTP DTO/routes/auth adapter
    application\              跨域用例、事务协调
    domain\workspace\          学习空间与身份引用
    domain\catalog\            知识节点、关系、单元
    domain\planning\           草案、版本、阶段与局部改动
    domain\resources\          资源记录、偏好与覆盖
    domain\reflections\        总结及修订反馈
    domain\practice\           项目、任务、Prompt、验收
    ports\                     LLM/Resource/GitHub/RAG/Repo/GraphRunner
    agent_workflows\           graph builders/state/nodes/routes
    infrastructure\            db/checkpointer/worker/providers/external
    core\                      id/error/config/request_id
  backend\tests\
  frontend\src\                api/generated / features / mocks
  contracts\                  openapi.json + examples + schema diffs
  docs\                       ADR/migration/design/acceptance
  scripts\                    safe start/test/export/verify
  var\                        仅本机数据，不入库
  .venv\                      仅本机解释器，不入库
```

B0 先评估旧目录已有结构，再决定目标目录是否需要按以上方式放置；**不要为符合此目录树而迁入整套旧依赖**。仓库根目录独立 Git、锁文件、`.gitignore`、`.env.example`、`README`，模块复用记录旧 HEAD 与原路径；新版本若已存在工作树，禁止覆盖。

## 2. 模块内聚、事务边界与可插拔矩阵

| 领域/模块 | 唯一职责 | Public interface（示意） | 禁止耦合 |
|---|---|---|---|
| workspace | 用户身份、学习空间、项目授权 | `AuthContext`/`WorkspaceService` | 客户端自报 tenant/actor |
| catalog | 节点、类型、关系、单元、依赖图校验 | `CatalogService` | 直接修改用户 Prompt/进度 |
| planning | 草案、计划版本、顺序、知识/实践关联 | `PlanningService` | 用图 checkpoint 作为正式计划 |
| resources | URL 可信状态、章节和偏好覆盖 | `ResourceIndexPort` | 自动断言课程质量或影响掌握评审 |
| reflections | 单元总结与 rubric 对照、修订历史 | `ReflectionService` | 自动把任务标验收通过 |
| practice | 主实践项目、阶段任务、修订、证据 | `PracticeService` | 直接执行外部 GitHub 仓库代码 |
| agent_workflows | 三张 StateGraph、状态转移、暂停/恢复 | `GraphRunnerPort` | 承担业务数据库所有权 |
| ai_gateway | provider、结构化输出、成本、失败分类 | `LLMPort` | 决定知识业务状态或写跨域表 |
| integrations | GitHub/RAG/URL external adapters | 协议化 Ports | 绕过身份权限、直接改业务表 |

跨领域写入由 application use case 组织，单个命令一个可辨识事务边界。普通 CRUD 和状态机不必用 LangGraph；只有有多步生成/有限修复/外部评审的任务使用 Graph。不要把规划拆成多个互相调用的 Agent 以追求形式上的多 Agent。

Port 最小形态（签名由 B1 实际 DTO 定稿）：
```python
class LLMPort(Protocol):
    def generate_structured(self, *, purpose: str, payload: dict,
                            schema_name: str, run_id: str, attempt_id: str) -> dict: ...
class ResourceIndexPort(Protocol):
    def find(self, *, scope: AuthContext, node_keys: list[str], preference: dict) -> list[ResourceDTO]: ...
class GitHubReferencePort(Protocol):
    def candidates(self, *, topic: str, constraints: dict) -> list[RepoCandidate]: ...
class RAGPort(Protocol):
    def retrieve(self, *, scope: AuthContext, query: str, limit: int) -> list[Evidence]: ...
class GraphRunnerPort(Protocol):
    def start(self, *, run_id: str) -> None: ...
    def resume(self, *, run_id: str, decision_id: str) -> None: ...
```
Ports 的契约测试必须同样作用于 Fake 和真实适配器，Failure DTO 不准静默转成空成功；fake 不允许部署为真实评审能力。`AuthContext` 由服务端从可信会话生成，不能作为前端请求体传入。

## 3. 业务实体、知识关联与数据约束

名词：`LearningProject` 是用户在平台的学习空间，`PracticeProject` 是用户拟开发的实际软件。`KnowledgeNode` 最小知识点；`LearningUnit` 是总结主体；`PlanRevision` 是路径结构快照；`PracticeTask` 是可验证交付物。

```text
Actor --membership--> LearningProject -- Preference
                           |-- PlanDraft -> PlanRevision -> PlanStage
                           |                             |-- PlanUnitLink -> LearningUnit
                           |                             |                     |-- UnitNodeLink -> KnowledgeNode
                           |                             |                                       |-- KnowledgeRelation
                           |                             |-- PlanTaskLink -> PracticeTask
                           |-- UnitProgress / SummaryAttempt -> SummaryReview
                           |-- PracticeProject -> PracticeTask
                           |                                |-- TaskKnowledgeLink -> KnowledgeNode
                           |                                |-- PromptRevision -> PromptReview
                           |                                |-- PracticeSubmission -> AcceptanceReview
                           |-- AiRun -> AiRunEvent / Attempt / checkpoint ref
KnowledgeNode -- NodeResourceLink --> ResourceRecord
```

最小表/重要字段：

| 表 | 重要字段 | 不变量 |
|---|---|---|
| `knowledge_nodes` | project_id, node_id, stable_key, title, type, objectives_json, content_version, source_status, supersedes_id? | 项目私有 AI 草稿；稳定键不等于标题；只在验证后共享 |
| `knowledge_relations` | scope, from_id, to_id, relation_type | prerequisite/contains/related/alternative；前置依赖无环；跨项目关系拒绝 |
| `learning_units` | unit_id, stable_key, title, rubric_json, rubric_version | 单元目标和评审版本可追溯 |
| `unit_node_links` | unit_id, node_id, order_index, role | 一个单元多节点，节点可复用 |
| `plan_drafts` | draft_id, project_id, run_id, revision_candidate, status, content_hash | 生成草案不可直接覆盖正式路线 |
| `plan_revisions` | plan_id, project_id, revision, goal_snapshot, status, created_at | 已确认结构不可变；同项目 revision 唯一 |
| `plan_stages/plan_unit_links/plan_task_links` | plan_id, stage_id, ref_id, order_index | 引用已有稳定实体，保持有序 |
| `unit_progress` | project_id, unit_id, status, version, updated_at | 跳过≠完成/掌握；不随 plan revision 替换 |
| `practice_projects` | project_id, practice_project_id, idea, repo_url?, status | 与学习空间不同概念 |
| `practice_tasks` | task_id, practice_project_id, stable_key, goal, in_scope_json, out_scope_json, acceptance_json, status, version | 一项任务一项可验收交付物 |
| `task_knowledge_links` | task_id, node_id, role | core/supporting/extension；多对多，不自动推断掌握 |
| `preferences` / `preference_overrides` | scope, media_type, language, official_priority, pace, version | 节点>单元>项目默认>系统默认；临时切换不写全局 |
| `resource_records` / `node_resource_links` | url, title, media_type, language, section_anchor, checked_at, verification_status, provenance | URL 可达≠内容质量；官方标签须有来源 |
| `summary_attempts/reviews` | attempt_id, unit_id, content, attempt_no, rubric_version, run_id, review_json | 原文和反馈不可变，重试不能多写 |
| `prompt_revisions/reviews` | revision_id, task_id, user_draft, export_text?, review_json, run_id | 导出绑定指定版本，不覆盖初稿 |
| `practice_submissions/acceptance_reviews` | submission_id, task_id, evidence_json, evidence_grade, conclusion, reviewer_kind | reported/verified/insufficient；基于证据说明结论 |
| `ai_runs`, `ai_run_events`, `ai_provider_attempts`, `ai_jobs` | actor_id, project_id, thread_id, graph_name/version, run_id, idempotency_key, attempt_id, status, lease_token | 外部 Run API 与内部 checkpoint 分离 |

**版本策略**：PlanRevision 与 Node/Unit content/rubric version 分别管理；局部重规划按已确认 stable_key 精确映射，不依据相近标题自动合并历史。学习成果始终挂载稳定单元/任务 ID 并保存当时的 rubric 版本；新 rubric 改动时旧总结保留，但不宣称已满足新目标。草案取消或生成失败时当前计划不变。正式发布必须在业务事务中执行：校验草案 hash + expected_version + 幂等键 → 新增 plan revision/links → 设置当前引用；在同一事务内落定。不能简单取版本最大值作为当前（未确认草案可能更新）。

**权限策略**：新私有表含项目归属或通过具有约束的归属链校验，采用数据库 RLS/应用查询双防线；索引、FK 与唯一约束覆盖项目作用域；后台 worker 只能获取合法 scope；不同用户/项目的 run、草案、总结、checkpoint 访问统一拒绝。旧身份/会话机制迁入前按最终开放注册版本复核，不能混入邀请兑换。

## 4. LangGraph 的三张小图

```text
planning_graph:
START -> normalize -> generate_outline -> build_dependencies_and_units
      -> propose_practice -> validate -> [repair ≤ 2] -> save_draft_projection
      -> await_approval [interrupt] -> (cancel | edit+validate | approve)
      -> commit_plan_idempotently -> END

summary_review_graph:
START -> load_rubric_snapshot -> review_once -> validate_review
      -> persist_review_idempotently -> END

prompt_review_graph:
START -> load_task_and_revision -> review_once -> validate_review
      -> persist_review_idempotently -> END
```

图执行不跨用户数月学习周期，只有规划可暂停等待用户；总结/Prompt 的每次修改是新的 `attempt/revision + run`。成果验收先用普通业务服务和按需模型调用，不建第四张空图。不要把按日计划、偏好和普通状态切换包装成 Graph。

**状态最小化**：Graph State 只存 `run_id/project_id/goal/prefs_snapshot/outline_ref/draft_ref/validation_errors/repair_count/decision/result_id` 等有限 JSON 可序列化字段；不写入密钥、无限历史、完整检索文本、二进制附件。必要的草案保存在受授权业务草案表，checkpoint 保存引用。图状态字段严格单写入者或明确 reducer，不依赖平行写同一键碰运气；规划验证包含依赖无环、顺序一致、任务知识关联合法、数量软上限、必填验收标准，内容修复次数上限 2，超限失败并保留错误。

**中断规则**：`interrupt()` 仅位于独立等待节点；在其前只做无副作用快照读取，不做付费模型调用或未保护写入。恢复必须由业务接口鉴权，以服务端映射 thread_id 和当时 graph_version 执行 `Command(resume=...)`，同一线程并发恢复串行化；编辑后重新验证。取消后的草案不得被 worker 稍后错误发布。不同版本 graph 的 waiting_user run 必须保持可恢复版本或明确安全终止，不能随部署升级直接重解释旧状态。

## 5. Run、队列、检查点和双写一致性

```text
POST AI action -> Auth + validated body + Idempotency-Key
               -> atomic: persist original input/draft + ai_run(queued) + ai_job
               -> 202 {run_id,status_url}
worker lease/claim_token -> record attempt before external call -> graph invoke
  -> checkpoint committed -> project result/draft to authorized RunView
  -> waiting_user / succeeded / failed / reconciliation_required
POST decision -> auth + expected_version + draft hash + idempotency
              -> transaction waiting_user -> queued + create resume job
worker -> claim_token -> graph Command(resume=...) on server-mapped thread_id
       -> idempotent domain commit -> run terminal state
```

三个权威来源：业务事实 = 领域表；Graph 断点 = Checkpointer；运行对外状态 = `ai_runs` 投影。Checkpoint 写入与领域事务不天然是一次原子提交，因此所有重要提交节点要 `run_id + operation_key` 唯一且可重放：检查业务是否已成功后再返回同一个结果，不允许重复创建计划、总结或导出。waiting_user 只能在可恢复 checkpoint 与草案投影均可读取后对外可见；中途崩溃由 recovery job 统一核对，不能让 UI 确认一份不存在的 checkpoint。Run 映射 `thread_id` 不返回客户端。

付费调用：同 `attempt_id`、供应商 id 和账务状态留存；已 dispatched 且上游结果未知不自动再次发起相同的付费操作，进入 `reconciliation_required` 或由用户明确开启新尝试。已落库结果重放走本地事实，不重调模型。重试仅对明确安全失败有界执行，不能被 Graph node replay 和 SDK 自动重试同时放大。数据库队列使用 lease、claim_token fencing、唯一 job key，恢复后仍查 Run/attempt 当前状态。业务提交、Run 终态与事件写入在可用时同事务；跨 Checkpoint 不能假设事务一致。

PostgreSQL 推荐：同一服务实例建 `studyplan_app` 和 `studyplan_checkpoint` 两个**独立数据库**，账号权限分开；测试用 `studyplan_test_*` 临时库。旧 E 盘数据库不作为新项目默认连接。实际 DSN 只放 `D:\studyplan\.env`，不入库；`.env.example` 使用占位值，不复制旧 secret。Checkpointer 的 `.setup()` 由受控 bootstrap 执行；生产使用 PostgresSaver/AsyncPostgresSaver，不能使用仅驻内存 Saver。将 `LANGGRAPH_STRICT_MSGPACK=true` 在进程启动/导入 LangGraph **之前**设定，关闭不必要的 pickle fallback，Checkpoint 数据只允许受限角色访问；敏感记录必要时加密与保留/删除策略。

用户删除项目时须撤销未完成 Run、禁止再恢复、清理领域记录与关联 checkpoint（分步可补偿），不能只删界面记录留下可恢复的草案。Checkpoint 保留周期不得早于 waiting_user 的合法恢复窗口。

## 6. 用户偏好、资源链接和 GitHub 参考

偏好优先级：节点临时选择 > 单元临时选择 > 学习空间默认 > 系统默认；`text_first/video_first/mixed/both`，语言和官方优先由用户修改。推荐结果包含媒体类型、语言、覆盖节点、出处、章节/视频时间点、核验时间与状态。HTTP 200 不能自动证明知识质量；找不到真实资源时返回 `unavailable` 和检索建议，不能伪造 URL 或视频时间戳。

GitHub 候选由 `GitHubReferencePort` 提供；检查仓库 URL、许可证、技术栈、代码规模、更新时间、README 与运行门槛，说明哪些只是候选事实而非已验证的课程质量；没有授权或限流时使用已校验小项目池/用户自给仓库链接。无论如何不得从搜索结果自动执行任意代码。外部网页/文档视为不可信数据，限制 URL scheme、私网地址/重定向/SSRF，限制下载体积与时长，不将页面内容提升为系统指令；内容展示做好 XSS 清洗。

RAG 在独立项目中维护。主项目只用 `RAGPort(scope, query, limit)` 获取已授权证据及引用，服务调用凭据独立；RAG 超时/失败只使相关补充资料不可用，不导致学习进度回滚，也不让模型伪造证据。

## 7. API、前后端契约与异步 UI

新业务 API 一律 `/api/v1`，项目内路径 `/api/v1/projects/{project_id}`。旧 API 转接时必须在 B0 产出路由清单并消除重复路径；不要同时暴露两套含义不同的 `/plan/generate`。`AuthContext` 源自 Cookie、签名会话与后端授权，不出现在可写请求体。生产同源反代 `/` React、`/api` FastAPI；开发 Vite `localhost:5173` 代理 `/api` 到 FastAPI `localhost:8000`；使用 `credentials: include`，Cookie 开发/生产策略区分且 CSRF/Origin 正确处理。

| 路径（省略项目内前缀） | 作用/返回 |
|---|---|
| `GET/PUT /preferences` | 有版本号的全局资源偏好与节奏 |
| `POST /plans/generate` | 202 `{run_id,status_url}`，创建规划草案运行 |
| `GET /runs/{run_id}` | RunView：状态、draft/result/error/next_action、version |
| `POST /plans/drafts/{draft_id}/decision` | approve/edit/cancel + expected_version + hash，202/结果 |
| `GET /plans/current`, `GET /plans/versions` | 已确认结构、历史版本及任务链接 |
| `GET /nodes/{node_id}`, `GET /units/{unit_id}` | 知识卡片、学习目标、来源链接、总结状态 |
| `PATCH /units/{unit_id}/progress` | 完成/跳过/返回学习，expected_version |
| `GET /nodes/{node_id}/resources`, `PUT/DELETE /preferences/overrides` | 节点资源与临时偏好 |
| `POST /units/{unit_id}/summaries` | 保存原文，202 review run；后查评审版本 |
| `GET /units/{unit_id}/summaries`, `GET /summaries/{id}/reviews` | 历史原文与反馈 |
| `GET/POST /practice-projects`, `GET /practice-tasks/{task_id}` | 软件项目/任务 |
| `POST /practice-tasks/{id}/prompt-revisions` | 保存用户方案，202 review run |
| `GET /practice-tasks/{id}/prompt-revisions`, `POST /practice-tasks/{id}/prompt-export` | 历史修订、按版本导出 |
| `POST /practice-tasks/{id}/submissions`, `POST /practice-tasks/{id}/acceptance-reviews` | 提交成果/有证据的评价 |

`GET /runs` 为长调用轮询基线，SSE 可按旧成熟事件回放实现但非必需 UI 功能。前端永不拿原始 Checkpoint/graph state/node 名；后端输出稳定 `next_action`。所有变更需 `expected_version` 或幂等键（按操作类型规定）；同键同体返回同结果，同键异体 409。固定分页、排序、null vs `[]` 语义、字段上限、时间 UTC ISO8601，错误视图含 `code/message/request_id/details` 且不回显敏感输入。FastAPI 的 Pydantic/OpenAPI 是契约真相源；从导出 JSON 自动生成 TypeScript 客户端，fixture 也由 DTO 校验。API 变更必须一起更新示例、文档和双方测试；前端样式可独立变化。

## 8. 状态枚举和产品用语

- UnitProgress: `not_started/in_progress/completed/skipped`；跳过不赋予掌握标签。
- SummaryReview: `satisfied/needs_revision/misconception`；仅说明本次提交与 rubric 的符合情况。
- PracticeTask: `pending/designing/prompt_reviewed/implementing/awaiting_evidence/accepted/skipped`；Prompt 通过不等于真实功能验收。
- EvidenceGrade: `verified/reported/insufficient`；明确平台是否真的验证过代码/结果。
- AiRun: `queued/running/waiting_user/succeeded/failed/cancelled/reconciliation_required`；图成功不自动等于知识已学会。
- Resource: `verified_candidate/unverified/unavailable`；资源可达、内容覆盖和教学质量分离。

## 9. 分级验收、合同测试和危险路径

| 层次 | 关键测试 |
|---|---|
| Domain | 前置依赖环；关系类型；进度/跳过；单元-任务多对多；偏好优先级；rubric/plan 双版本 |
| API | Pydantic schema、OpenAPI 示例一致、非法身份字段拒绝、404/409、Idempotency-Key、字段上限 |
| Graph | 结构有效/无效与两次修复上限；fake provider；interrupt/edit/approve/cancel；重启恢复；不同 graph version |
| Queue | 重复点击/重复投递；lease fencing；同 thread 双 resume 竞争；提供商超时结果未知不能盲重试 |
| Database | RLS 受限角色测试；事务原子发布；重规划保持提交；checkpoint 与 run 投影恢复一致 |
| Integration | 真云模型成功与失败；资源无效；GitHub/RAG 故障降级；安全来源引用 |
| E2E | 新注册→新目标→草案确认→资源偏好→总结→方案评审→导出→外部结果→验收→重登陆 |

最小日志 `request_id/run_id/graph_name/graph_version/node_name/attempt_id/provider/model_id/prompt_version/latency/input_tokens/output_tokens/cost/error_class`；不将原文总结、完整用户 Prompt、密钥直接放明文日志。数据保留、删除、敏感字段清理、跨租户数据访问须单独验证。CI/本地基本检查：领域测试 + HTTP contract + Graph fake + Postgres adapter/迁移 + 冒烟；高并发大规模压测延后，但不延后租户/幂等/事务正确性。

## 10. 提前冻结的 ADR 与待实证事项

| 决策 | 结论 |
|---|---|
| 文件路径 | 旧 E 盘只读、新 D 盘唯一开发；不复制旧虚拟环境/密钥/运行数据 |
| 工作流 | 三张小 StateGraph；不引入全生命周期大图或重复业务流程引擎 |
| 数据权威 | 业务表 / Checkpoint / RunView 三类状态分离 |
| 知识质量 | AI 生成先为项目草稿，不自动成为全局共享知识 |
| 路线确认 | 只有用户确认的 PlanRevision 是当前路线 |
| 成果/进度 | 总结、Prompt 评审与实际验收三者独立 |
| 资源 | 已验证来源优先，临时偏好不改变全局 |
| 契约 | Pydantic/OpenAPI 唯一源，TS 类型自动生成 |
| 演进 | RAG/GitHub/模型按 Port 插拔，禁跨域直连私有表 |
| 安全 | 旧开放注册要求不回退，隔离/幂等/断点恢复属阻断门禁 |

B0 必须实际查清：本机 `E:` HEAD、未提交内容、最终认证版本与邀请码清理、迁移 head、旧 DB 角色权限、真实 provider、旧 worker/queue 依赖、当前前端是什么；`D:` 是否已有数据；旧代码使用的第三方许可证及可搬运依赖。未经本机证据不能标为“已复用成功”。

## 11. 参考
- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://reference.langchain.com/python/langgraph.checkpoint.postgres
- https://reference.langchain.com/python/langgraph.checkpoint
- https://fastapi.tiangolo.com/advanced/generate-clients/
