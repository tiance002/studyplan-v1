# 学习规划助手 V1.1：实施方案（LangGraph + 新旧工程隔离）

> 版本 V1.1-LG，日期 2026-09-27。此文件为**待实施设计**，不是代码运行报告。配套 `SOFTWARE_DESIGN.md`、`FRONTEND_HANDOFF.md` 与 `B0_CODEX_GOAL.md` 共同组成开发基线。

## 当前批次边界（2026-09-29）

B3-F1 将普通浏览器注册登录提前交付，并接通正式 React 前端和阶段只读聚合。原计划中 B6 的认证排期及 B3 最小单用户会话描述是历史排期，不再代表当前实现。执行边界以 `docs/development/B3-F1-scope.md` 为准；B3-F1 完成后停止，不自动启动 B3-F2。旧工程在本批次完全不操作。

## 0. 冻结决策和机器路径

| 名称 | Windows 路径 | 允许事项 | 禁止事项 |
|---|---|---|---|
| LEGACY_ROOT | `E:\codex_workspace\study-plan` | 只读查看、执行不会修改源码/数据的审计、确定被复用模块及 HEAD | 原地重构、清库、删除、在旧目录提交新版、无证据安装或修改依赖 |
| NEW_ROOT | `D:\studyplan` | 新建独立工程、选择性复制代码、开发测试、独立 Git 历史 | 不经审计直接全量复制旧工程、复用旧数据库或旧密钥 |

无法从远端访问用户的本机 E/D 盘。本文件没有声称对本机目录或未推送分支完成审计。B0 必须以本机真实 HEAD、工作区变更和运行事实为准；GitHub 默认分支仅是参考样本。若 `D:\studyplan` 已有仓库/文件，先盘点和备份，不执行 `git init`、覆盖、删除或重置，除非已确认安全。

**新旧隔离**：新工程独立 `.git/`、`.venv/`、`.env`、`var/`、日志、端口和数据库；旧路径不进入新运行配置，不通过 symlink/junction 连接旧工作区。不复制 `.git/`、`.venv/`、`__pycache__/`、`node_modules/`、`.env*`（仅人工重建 `.env.example`）、`var/`、本地数据库、审计/密钥、上传文件及旧 Checkpoint。复制模块时记录 `legacy HEAD / 源路径 / 目标路径 / 许可证 / 修改原因 / 测试证据`。

可按 `D:\studyplan` 独立 Git 根组织：`backend/`、`frontend/`、`contracts/`、`docs/`、`scripts/`、`tests/`、`.venv/`（忽略）、`var/`（忽略）。新版固定 `D:\studyplan` 是工作目录，不要把设计包所在 `/mnt/data` 当成用户本机工程路径。

## 1. 产品 V1 范围

目标用户：希望学习 Agent 开发、云服务等可落地工程领域，并能借助 AI 编码工具形成实际项目的人。统一按零基础生成知识体系；用户可跳过、返回、修改资源偏好。用户不依赖本平台执行代码，平台指导其组织思路、评审 Prompt，外部平台实施后再提交成果。

核心业务链：**学习目标（项目想法可选）→全量领域索引纲要→知识节点/单元/前置关系→路径草案→确认→当前单元资料链接→自主总结→AI 引导反馈→阶段项目任务→用户编写实现思路→AI 评审→导出 Prompt→外部实现→证据验收→进度/下一阶段**。

| P0 必须有 | V1 最小交付方式 |
|---|---|
| 统一从零规划与可跳过 | 不做基础评估；跳过与完成、掌握相互独立 |
| 体系/单元/路线 | 一次生成完整可浏览纲要，详细卡片按需展开；依赖不成环 |
| 路线确认和再规划 | 草案与正式版本分离；局部修改、保留旧总结/任务 |
| 资源偏好与索引 | 全局/单元/节点优先级；有限的真实、已检查资源池；失效如实标记 |
| 用户总结与反馈 | 用户先写，模型依据单元目标提出缺口和引导问题；允许结束/跳过 |
| 主实践项目 | 用户提供想法或从候选中选；围绕一个项目迭代，按阶段拆分有验收的任务 |
| Prompt 评审与导出 | 原始草案+多次修订；导出绑定确定版本；警告不等于强制死循环 |
| 成果验收 | 区分用户自述、外部报告和本系统实际可核验证据 |
| 后端可独立使用 | OpenAPI、fixtures、真实 PostgreSQL、真实云模型、单独 worker、pytest |

GitHub 参考项目：V1 必须有候选显示/手动 URL 接入和许可证/规模/技术栈的元数据结构；有网络时可调用 `GitHubReferencePort`，但其不可用时已验证的小项目池不阻断闭环。**不得自动 clone 并运行外部仓库代码。** 用户学习资料优先索引地址/章节，不批量复制第三方全文。不做长期能力评分、复杂图谱、全网课程质量分、多模型精细路由、自动在线代码运行或微服务治理。

## 2. 复用与迁移策略（按本机证据决策）

| 旧能力 | 新版判定方向 | 迁移原则 |
|---|---|---|
| `core` ID/hash/error/request-id/idempotency | 优先复制/适配 | 单一实现，配套测试；脱离旧依赖后可独立使用 |
| 身份/注册/登录/Cookie、`tenancy` | 复用最终开放注册版本 | 保留中文用户名、6–12 位密码、无邀请码的既定产品约束；密码安全散列/限流/会话安全仍需验收；禁止从旧默认分支恢复邀请码 |
| PostgreSQL、Alembic、RLS | 选择性复用机制 | 新数据库和新迁移基线；不要把旧迁移序号直接套在新库上；新表按项目授权 |
| `product` 项目、会话、计划版本/任务 | 拆领域复用 | 保留项目与版本设计、单独新增知识结构/单元/实践关系；不要靠旧任务 `title` 承载全部字段 |
| `learning` 提交/证据 | 选择性复用 | 历史不可变提交思路保留，V1 不使用旧掌握度打分决定学习进度 |
| `teaching` provider/attempt/budget/run | 提取通用部分 | 不复用“有检索引用才允许回答”的教学结论门作为所有规划任务门；真实 Provider 是否存在以本机为准 |
| `knowledge` 解析/检索/引用 | 交由独立 RAG 项目维护 | 主项目保留资源 URL 元数据/来源引用与 `RAGPort`；不在新主服务继续发展另一套索引引擎 |
| 旧 `workflow/registry/execution/policy` | 安全机制按需抽取、旧图隔离 | LangGraph 是新业务编排唯一入口；不能同时有两个争夺业务状态的工作流引擎 |
| 旧单页 HTML | 仅参考旧行为 | React/TS/Vite 正式前端；旧 HTML 不定义新 API |

**迁移不是一键复制。** B0 输出逐模块 `copy/adapt/reference-only/drop` 清单；B1 才按依赖闭包选择性迁入。对于需要大量旧框架才能运行的少量通用函数，优先按其契约重新实现最小模块并保留出处和测试，而不是搬整个旧执行引擎。禁止为了兼容已放弃的旧业务数据，构建长期双模型/双 API 兼容层。

## 3. 技术方案

- 前端：React + TypeScript + Vite；同源反代 `/api/v1`，前端仅使用 OpenAPI 生成的 typed client。
- 后端：FastAPI + Pydantic；清晰的 API/Application/Domain/Infrastructure 分层；当前仅一个主业务服务。
- Agent：LangGraph `StateGraph`，三张小图（规划、总结评审、Prompt 评审）；轻量领域规则/应用服务承担普通 CRUD、状态、成果验收。
- 数据：PostgreSQL 业务库 + 同 PostgreSQL 实例的独立 Checkpoint 数据库与受限角色；Alembic 管理业务结构；Graph `thread_id` 由服务端创建并映射。
- 异步：主服务创建 `ai_run` 与持久任务；worker 领取后驱动 Graph；HTTP 返回 202，轮询为 V1 基线，SSE 仅为体验增强。
- 模型：一个统一 `LLMPort`，云模型先行，Fake 仅用于测试；本地模型后续可插拔而不污染领域层。
- 外部：`ResourcePort`、`GitHubReferencePort`、`RAGPort`；真实服务故障时只做明确降级，不伪造资源或评审。

## 4. 后端与前端并行的冻结时点

B1 结束冻结领域术语、状态枚举、Pydantic 请求/响应、统一错误体、运行生命周期、Mock 样例、OpenAPI v1。前端可以改变树/图/卡片展示、布局与组件库，但不能自行定义业务状态、Graph 内部节点或自报用户/租户身份。

运行契约：`POST` AI 操作创建 `run_id`；`GET /runs/{run_id}` 返回 `queued/running/waiting_user/succeeded/failed/cancelled/reconciliation_required` 与 `next_action`；`waiting_user` 的草案预览确认走业务 API。浏览器断线不等于取消任务。统一 400/401/403/404/409/422/429/503，错误体保留 `request_id`，用户可恢复编辑内容。

## 5. 开发里程碑：独立 Goal，小范围验收

### B0：本机事实审计、隔离和复用清单
读取 `LEGACY_ROOT` 的分支、HEAD、dirty files、运行/测试/迁移现状，确认 `NEW_ROOT` 是否已有数据；不在旧目录产生写入。建立备份/来源清单、项目依赖图、认证现状、迁移策略与独立目录方案。产出 `docs/migration/legacy-inventory.md`、`module-reuse-matrix.md`、`source-provenance.md`、`docs/adr/`。若旧工作树存在未提交修改，先保全并记录，绝不覆盖或盲拷。**本批次不进行全仓库迁移。**

验收：旧目录源码/数据哈希和 Git 状态无意外变化；新目录身份清晰；复用条目每项都标明证据和依赖，未验证标 `unverified`。

### B1：新骨架、领域契约与 Graph 最小恢复演练
在 `D:\studyplan` 建独立后端/前端占位、统一启动配置和可测试新库；定义领域 ID、DTO、状态枚举与 OpenAPI、JSON 示例；按 B0 选择性迁入认证和核心 utils；搭建最小 `ai_runs`/queue 与 `StateGraph` Fake 图，验证 Postgres checkpoint、interrupt/resume/重启恢复。前端自此开始 Mock 设计；B1 的样例数据与 OpenAPI 匹配后才标“契约冻结”。

验收：目录不依赖 E 盘而启动；只用 Fake 的断点可跨进程恢复；run 越权拒绝；OpenAPI 无重复 operationId；前端可生成 TypeScript client。

### B2：知识与计划业务域
实现知识节点/关系/单元/路径草案与发布、路径版本、进度、实践任务与知识多对多、偏好/资源表、核心迁移与权限。使用固定示例数据完成「创建→草案→确认→跳过→重新规划→进度保留」。同一计划草案重复确认不能重建两份；编辑必须重新验证。

### B3：真实规划 Graph 与云模型
接入真实云模型、结构化输出和受控修复（至多 2 次）；先纲要再分期详情；合法草案发布前需用户确认；无项目想法提供候选项目或可延后选择；资源检索不阻断结构生成。每次模型调用记录 attempt/model/prompt/schema/成本。真实端到端可通过 API 演示。

### B4：资源索引与总结闭环
加入有限真实资源池与验证元数据，按全局/单元/节点偏好排序；总结提交保存原文和 rubric 版本，图生成 covered/gaps/misconceptions/questions；每次修订创建独立 run，不让长期 Graph 挂起数月；允许补学/跳过。

### B5：项目实践与 Prompt 工作台后端
任务绑定核心/支撑/扩展知识；用户先写方案；图评审并保存修订、可导出指定版本；外部开发结果/日志/仓库链接以证据等级归档；接受/待补充/未通过分明；不因 AI 生成代码报告直接声明系统已验证。

### B6：前后端联调与可交付验收
React 接 OpenAPI typed client；用户完成注册、创建目标、确认计划、资源切换、总结、Prompt、导出、提交成果和验收，重新登录数据保持。测试错误/重复/断线/等待用户/服务不可用等边界。拆出后续 P2/P3 队列，不以高并发优化阻断首版。

### 开发顺序调整说明
- B0 只能审计与准备，**不能在 E 盘建立新版开发分支**；新 Git 只在 D 盘。
- B1 先确立领域契约和最小可运行 Graph，再开发全部领域表；避免 Graph 在实体未定时写死逻辑。
- B2 固定业务事实结构，B3 才接真模型；B4/B5 可并行开发，但共同依赖 B1/B2 的接口。
- 各 Goal 均要求 `Goal / Constraints / Allowed changes / Non-goals / Tests / Evidence / Rollback`，不交付一份一次性包揽 B0–B6 的巨型 Goal。

## 6. 故障、成本及质量优先级

**阻断 V1**：认证/项目越权、数据丢失、Graph 跨用户恢复、重复批准造成重复计划、重复付费派发、无法恢复核心流程、误把模拟器当真实模型、错误宣称安全/工程验收已通过。**可后延**：精美知识图谱、高并发调优、全网资源评分、多层记忆/模型路由、全面自动项目测试、SSE 动效。对外部副作用的未知结果不自动重派；模型失败保留原文与草案，允许人工核对/重新启动新的明确操作。

控制用量：outline 先行、卡片按需展开、每单元默认一次总结、每阶段默认一项主实践；模型输入只带授权项目上下文和必要节点；资源/偏好/进度用确定性代码；结构校验失败至多 2 次修复；无真实 provider 时明确失败而非输出假内容。

## 7. V1 验收情景

用户零基础学 Agent，主项目 PDF 知识助手：无需诊断生成知识索引，用户确认路线；跳过 Python 基础后仍可返回；文字默认+单节点视频覆盖；用户总结 RAG 后模型指出检索策略缺口；用户自己写 PDF 上传方案，经评审导出指定版本 Prompt；外部工具执行后提交结果，平台将自述、报告、实际验证区分；重规划不删除总结与成果；其他用户访问同一资源 ID 或 run ID 被拒；关停 worker/重启再恢复 waiting_user；缺 RAG/GitHub 网络也能使用已有资源池完成闭环。

## 8. 外部文档核对（以安装的锁定版本为准）
- https://docs.langchain.com/oss/python/langgraph/graph-api
- https://docs.langchain.com/oss/python/langgraph/interrupts
- https://docs.langchain.com/oss/python/langgraph/persistence
- https://reference.langchain.com/python/langgraph.checkpoint.postgres
- https://fastapi.tiangolo.com/advanced/generate-clients/
