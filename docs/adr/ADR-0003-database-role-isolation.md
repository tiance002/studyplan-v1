# ADR-0003：数据库与 Checkpoint 使用独立库、独立角色

- **状态**：Accepted（B0 冻结）
- **日期**：2026-09-27
- **关联**：`SOFTWARE_DESIGN.md` §3 §5 §9 §10、ADR-0002

## 背景

旧工程 `E:\codex_workspace\study-plan` 的数据库形态（来自本机审计）：

- `alembic/versions/` 已被压成**单头** `0001_initial_schema.py`，它是原 head `0021` 的**全部有效对象合并快照**，含表、列、约束、索引、**RLS 策略**、`GRANT`、`SECURITY DEFINER` 函数、角色断言块。
- 迁移**不建 role、不建 extension**；角色不存在时**显式失败**（而非静默建库或降级）。
- `alembic.ini` 明文记录：**迁移角色与应用角色必须不同**。迁移需要 DDL 权限，而应用角色 `study_app` **不得**有 DDL，否则"一个失误就能改表结构或绕过 RLS"。
- `alembic.ini` 还记录了另一个真实事故：它保持**纯 ASCII**，因为 configparser 以 `encoding="locale"` 读取，中文 Windows 上即 GBK，**UTF-8 中文注释会让 `alembic` 在任何自有 Python 代码运行前就 `UnicodeDecodeError`**。

新版还需新增一个数据库：LangGraph 的 Checkpoint 库。

## 决策

在同一 Postgres 实例上建立**两个独立数据库、三个独立角色**：

| 数据库 | 角色 | 权限 | 用途 |
|---|---|---|---|
| `studyplan_app` | `studyplan_app` | DML + 受 RLS 约束的读写；**无 DDL** | 业务事实源（领域表） |
| `studyplan_app` | `studyplan_migrator` | DDL | Alembic 迁移 |
| `studyplan_checkpoint` | `studyplan_checkpoint` | DML（由 LangGraph `.setup()` 建表） | 图断点 |
| （测试） | — | — | `studyplan_test_*` 临时库，测试后销毁 |

配套约束：

- **C11**：迁移角色与应用角色强制分离。禁止授予 `studyplan_app` 任何 DDL。
- **C9**：迁移**不建 role、不建 extension**；角色不存在时**显式失败**。
- **C10**：`alembic.ini` 保持**纯 ASCII**（中文注释一律放 `.py` 或 `.md`）。
- **新迁移基线**：不复用旧 `0001` 的 revision id 与表结构。旧 0001 是为旧业务域而建（含 `routing_decision`、`acquisition_fetch_observations`、`study_metrics_snapshot()` 等新版不需要的对象），设计文档 §2 明确「不要把旧迁移序号直接套在新库上」。
- **RLS 双防线**：新私有表含项目归属，或通过有约束的归属链校验，采用数据库 RLS + 应用查询双防线；索引、FK、唯一约束覆盖项目作用域。
- **Checkpointer bootstrap 受控**：`.setup()` 不进应用启动路径，由独立脚本执行（`scripts/`）。
- **旧数据库不作为新项目默认连接**：`.env.example` 中不含任何旧 DSN。实际 DSN 只放 `D:\studyplan\.env`，不入库。
- **测试库隔离**：需要 Postgres 的测试用 `studyplan_test_*` 临时库；不可达时整组**跳过**（沿用旧工程的 marker 思路）。本次 B0 未连接任何数据库（任务禁止），因此**未验证旧库实际角色权限** —— 标 `unverified`。

## 后果

**正面**

- 应用层即使存在 SQL 注入或逻辑缺陷，也无法 `ALTER TABLE` 或 `DROP`，更无法绕过 RLS。
- Checkpoint 库被攻破不影响业务事实源，反之亦然。
- 测试可安全地建/删临时库，不会碰生产数据。

**负面 / 代价**

- 本地开发需建 2 个 database + 3 个 role，bootstrap 步骤比单库多。**缓解**：`scripts/` 提供受控 bootstrap 脚本，README 记录步骤。
- 两个库之间无法使用外键或跨库事务，一致性靠应用层 `run_id + operation_key` 幂等保证（见 ADR-0002）。

## 拒绝的备选方案

| 方案 | 拒绝理由 |
|---|---|
| 单库单角色 | 应用角色将被授予 DDL 或被 RLS 绕过；旧工程已用注释明确这是禁止的 |
| 单库双 schema | 权限隔离靠 schema `GRANT` 可行但易错；且 LangGraph 建表会污染业务库命名空间 |
| 用 `MemorySaver` / SQLite 做 checkpoint | 违反"生产不得使用仅驻内存 Saver"；SQLite 无法多 worker 竞争 |
| 复用旧 `0001` 迁移 | 带入新版不需要的旧业务对象，且 revision id 与旧库耦合 |
