# ADR-0002：业务事实、图断点、运行投影三类状态分离

- **状态**：Accepted（B0 冻结）
- **日期**：2026-09-27
- **关联**：`SOFTWARE_DESIGN.md` §1 §3 §5 §10

## 背景

引入 LangGraph 后，系统里同时存在三类"看起来都像状态"的东西：

1. 领域表（`PlanRevision`、`UnitProgress`、`SummaryAttempt` …）；
2. LangGraph Checkpointer 里的图状态（`run_id` / `node` / `interrupt` 位置）；
3. `ai_runs` 表（对外可授权的运行状态）。

一个自然的偷懒做法是"图状态就是业务状态"——把计划直接存进 checkpoint，前端从 checkpoint 读进度。这会同时破坏权限模型、事务语义与演进能力：

- Checkpoint 由 LangGraph 序列化（msgpack），形状受框架版本控制，**不能**作为对外契约；
- Checkpoint 写入与领域事务**不天然是一次原子提交**，把业务事实放进去意味着"网页看到计划已生成，但计划表里没有"；
- Checkpoint 库需要独立角色与受限访问，若它持有业务事实，则权限模型必须复制到它身上。

## 决策

**三个权威来源严格分离，彼此不得越界**：

| 权威 | 存放地 | 唯一职责 | 对外可见性 |
|---|---|---|---|
| 业务事实 | `studyplan_app` 领域表 | 进度、计划版本、总结、任务、成果、资源元数据。**唯一真相** | 经 `/api/v1` 业务接口 |
| 图断点 | `studyplan_checkpoint`（**独立数据库、独立角色**） | 只保存工作流**执行位置**，保存业务对象的**引用**而非内容 | **永不**对外暴露；`thread_id` 不返回客户端 |
| 运行投影 | `ai_runs` (+ `ai_run_events` / `ai_provider_attempts` / `ai_jobs`) | 可授权的 RunView：`status` / `next_action` / 稳定错误码 | 经 `GET /runs/{run_id}` |

配套硬约束：

- Checkpoint 库与业务库是**同一 Postgres 实例上的两个独立 database**，账号权限分开；禁止同库同 schema。
- `LANGGRAPH_STRICT_MSGPACK=true` 必须在 **import langgraph 之前**设定（新版落地位置：`backend/app/agent_workflows/_msgpack_guard.py`，B1 实现），关闭 pickle fallback。
- Checkpointer 的 `.setup()` 由**受控 bootstrap** 执行，不在应用启动时隐式建表。
- 跨 Checkpoint 的提交**不能假设事务一致**，因此所有重要提交节点用 `run_id + operation_key` 唯一且可重放。
- 用户删除项目时须**撤销未完成 Run、禁止再恢复、清理领域记录与关联 checkpoint**（分步可补偿），不得只删界面记录。
- Checkpoint 保留周期**不得早于** `waiting_user` 的合法恢复窗口。

## 后果

**正面**

- 前端永远拿不到图内部结构（node 名、graph state），后端可自由重构图而不破坏契约。
- 领域层可独立测试（无 LangGraph、无 Postgres）。
- 权限只需在业务库与 `ai_runs` 上实施；Checkpoint 库物理隔离即可。

**负面 / 代价**

- 需要写"恢复核对"逻辑：崩溃后由 recovery job 核对 Run / checkpoint / 领域表三者一致，不能只信一个。
- `waiting_user` 对外可见的前提是「**可恢复 checkpoint 与草案投影均可读**」，实现上必须显式检查，而不是设完状态就返回。
- 开发期需要两类数据库，本地 bootstrap 步骤变多（`.env.example` 已提供两个 DSN 占位）。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 用 checkpoint 当业务事实源 | 破坏权限模型与事务语义；框架升级即破坏数据 |
| 用 `ai_runs` 当业务事实源 | `ai_runs` 是**投影**，用户删除/重放时会重建；它不是真相 |
| Checkpoint 与业务表同库 | 角色权限无法分离，一个误操作可同时污染两者 |
| 用 `MemorySaver` 做生产 | 进程重启即丢失断点，违反「跨进程恢复」验收条款 |
