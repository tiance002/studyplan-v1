# ADR-0005：LangGraph 三张小图是唯一业务编排层（不迁旧 workflow runtime）

- **状态**：Accepted（B0 冻结，B1 实现）
- **日期**：2026-09-27
- **关联**：`SOFTWARE_DESIGN.md` §2 §4 §10、`IMPLEMENTATION_PLAN.md` §2
- **本 ADR 直接回应 B0 验收条款「拒绝全仓库复制与重复构建执行引擎」**

## 背景

本机审计确认：旧工程**完全没有 LangGraph 依赖**。旧系统的编排由 `backend/app/workflow/runtime.py`（**840 行**，单文件）承担，配套 `workflow/{catalog,context,run_budget,runtime_idempotency,tools_impl}.py`（合计 1,587 行），另有 `execution/{state_machine,confirmation,outbox,child_run}.py`（703 行）实现租约、确认与 outbox。

因此存在一个真实诱惑：**"旧 runtime 已经跑通了，迁过来省事"**。

这个诱惑必须被明确拒绝，理由有三：

1. **双引擎**：设计 §2 明文「LangGraph 是新业务编排唯一入口；**不能同时有两个争夺业务状态的工作流引擎**」。若旧 runtime 与新 LangGraph 并存，两者都会想写 `ai_runs` 与领域表，一致性问题无法收敛。
2. **旧 runtime 承载的是旧业务语义**：它服务的是旧 knowledge / teaching 域，而 `knowledge/` 整体已被判定 `drop`（交由独立 RAG 项目）。搬 runtime 会连带搬回被 drop 的域。
3. **旧 runtime 是单体 840 行**：其内部耦合度使"只取通用部分"实际上不可行 —— 会变成"搬 840 行然后删掉一半"，比按契约重写更慢且更易引入死代码。

## 决策

**新版使用 LangGraph 的三张小 `StateGraph`，作为唯一业务编排层；旧 `workflow/` 与 `execution/` 全部 `drop` / `reference-only`。**

| 图 | 流程 | 特性 |
|---|---|---|
| `planning_graph` | `START → normalize → generate_outline → build_dependencies_and_units → propose_practice → validate → [repair ≤2] → save_draft_projection → await_approval(interrupt) → (cancel \| edit+validate \| approve) → commit_plan_idempotently → END` | **唯一可暂停等待用户**的图 |
| `summary_review_graph` | `START → load_rubric_snapshot → review_once → validate_review → persist_review_idempotently → END` | 无 interrupt |
| `prompt_review_graph` | `START → load_task_and_revision → review_once → validate_review → persist_review_idempotently → END` | 无 interrupt |

配套硬约束（部分来自旧代码的实测教训 —— 见 `module-reuse-matrix.md` §3）：

- **C8（源自旧 `openai_provider.py`）**：`LLMPort` 适配器**不自动重试**；已 dispatched 且上游结果未知**不自动再次发起相同的付费操作**，进入 `reconciliation_required`。禁止让「Graph node replay」与「SDK 自动重试」**同时**放大重试。
- **C7（源自旧 `providers_factory.py`）**：provider 凭据缺失时**拒绝启动**，绝不静默退回模拟器；Fake 只用于测试，**不允许部署为真实评审能力**。
- **状态最小化**：Graph State 只存有限 JSON 可序列化字段（`run_id` / `project_id` / `goal` / `prefs_snapshot` / `outline_ref` / `draft_ref` / `validation_errors` / `repair_count` / `decision` / `result_id`）。**不写**密钥、无限历史、完整检索文本、二进制附件。必要草案存受授权业务草案表，checkpoint 只保存**引用**。
- **`interrupt()` 只在独立等待节点**；其前只做无副作用快照读取，**不做付费模型调用或未保护写入**。
- **恢复必须鉴权**：以服务端映射的 `thread_id` 与当时 `graph_version` 执行 `Command(resume=...)`；同一线程并发恢复**串行化**；编辑后**重新验证**。
- **不同 graph version 的 waiting_user run 必须保持可恢复版本或明确安全终止**，不能随部署升级直接重解释旧状态。
- **内容修复上限 2 次**，超限失败并保留错误。

## 后果

**正面**

- 单一编排引擎，业务状态写入路径唯一，一致性可推理。
- 三张小图各自可独立测试（Fake provider + 内存 saver），不需要启动整个系统。
- 普通 CRUD 与状态机不进 Graph，避免"为了多 Agent 而拆多 Agent"。

**负面 / 代价**

- 放弃旧 runtime 已积累的边界处理经验。**缓解**：`module-reuse-matrix.md` §3 已把其中 12 条硬约束转写为 B1 验收项（尤其 C6 租约/状态过滤、C8 不盲重试）。
- 需要自行实现 lease / claim_token fencing / recovery job（旧 `execution/` 有 703 行参考实现，**仅作 reference**）。
- LangGraph 是全新依赖，需按其锁定版本核对 interrupt / persistence 行为。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 迁旧 `workflow/runtime.py` 作为编排层 | 直接违反设计 §2"唯一入口"；且绑死已 drop 的 knowledge/teaching 域 |
| 旧 runtime 与 LangGraph 并存 | 两个引擎争写业务状态，一致性无法收敛 |
| 把旧 runtime 改造成 LangGraph 的 node 实现 | 等于在编排层内嵌第二套调度语义（`run_budget` / `tools_impl`），复杂度不降反升 |
| 用一张大图覆盖全生命周期 | 设计 §4 明确禁止：图执行不跨用户数月学习周期 |
| 为成果验收再建第四张图 | 设计 §4 明确：先用普通业务服务 + 按需模型调用，不建空图 |
