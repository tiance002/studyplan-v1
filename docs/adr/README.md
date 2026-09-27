# 架构决策记录（ADR）索引

> V1.1-LG · 学习规划助手 · 2026-09-27
> 本目录记录**已冻结**的架构决策。每条 ADR 都包含：背景、决策、后果（正面与负面）、以及**被拒绝的备选方案及其理由**。
> 新增决策请沿用同一模板，编号递增，**不要修改已 Accepted 的 ADR 正文**（要改就写新 ADR 声明取代关系）。

## 决策清单

| 编号 | 标题 | 状态 | 冻结于 | 关联设计章节 |
|---|---|---|---|---|
| [ADR-0001](ADR-0001-independent-git.md) | 新版使用独立 Git 仓库与独立历史 | Accepted | B0 | §0 §10 |
| [ADR-0002](ADR-0002-three-state-authorities.md) | 业务事实、图断点、运行投影三类状态分离 | Accepted | B0 | §1 §3 §5 |
| [ADR-0003](ADR-0003-database-role-isolation.md) | 数据库与 Checkpoint 使用独立库、独立角色 | Accepted | B0 | §3 §5 §9 |
| [ADR-0004](ADR-0004-api-contract-openapi.md) | `/api/v1` 为唯一契约源，Pydantic/OpenAPI 驱动 TS 客户端 | Accepted | B0 | §7 |
| [ADR-0005](ADR-0005-langgraph-single-orchestrator.md) | LangGraph 三张小图是唯一业务编排层（不迁旧 workflow runtime） | Accepted | B0 | §2 §4 |
| [ADR-0006](ADR-0006-auth-policy-open-registration.md) | 认证保持开放注册 / 中文用户名 / 6–12 位密码 / 无邀请码 | Accepted | B0 | §3 §10 |

## 与设计文档 §10「提前冻结的 ADR」的对应关系

`SOFTWARE_DESIGN.md` §10 列出了 10 条冻结决策，其在本目录中的落点：

| 设计 §10 条目 | 落点 |
|---|---|
| 文件路径：旧 E 盘只读、新 D 盘唯一开发 | ADR-0001 + `docs/migration/legacy-inventory.md` §7 |
| 工作流：三张小 StateGraph；不引入全生命周期大图 | ADR-0005 |
| 数据权威：业务表 / Checkpoint / RunView 三类状态分离 | ADR-0002 |
| 知识质量：AI 生成先为项目草稿 | ADR-0004（契约层）+ `module-reuse-matrix.md` §1.2（knowledge `drop`） |
| 路线确认：只有用户确认的 PlanRevision 是当前路线 | 已由 `domain/planning/models.py` 实现（B0 已核实） |
| 成果/进度：总结、Prompt 评审与实际验收三者独立 | 已由 `domain/reflections/models.py` + `domain/enums.py` 实现（B0 已核实） |
| 资源：已验证来源优先，临时偏好不改变全局 | 已由 `domain/resources/models.py` 实现（B0 已核实，含 SSRF 防护） |
| 契约：Pydantic/OpenAPI 唯一源，TS 类型自动生成 | ADR-0004 |
| 演进：RAG/GitHub/模型按 Port 插拔 | `module-reuse-matrix.md` §1.2（`RAGPort` 边界） |
| 安全：旧开放注册要求不回退；隔离/幂等/断点恢复属阻断门禁 | ADR-0006 + ADR-0002 + ADR-0003 |

## 待 B1 决定的事项（尚未构成 ADR）

以下事项 B0 已识别但**证据不足以冻结**，B1 需先取证再补 ADR：

| 事项 | 待取证内容 | 相关 unverified |
|---|---|---|
| 真实云模型 provider 选型 | 本机是否曾成功调用；成本与限流策略 | `legacy-inventory.md` §4.2 |
| LangGraph / checkpoint-postgres 锁定版本 | 按安装版本核对 interrupt / persistence 行为 | 设计 §8 参考链接 |
| 新迁移基线的表结构 | 旧 0001 为旧业务域而建，新版需重设计 | `legacy-inventory.md` §4.3 |
| 会话载体细节 | Bearer → 签名 Cookie 的 CSRF/Origin/SameSite 方案 | ADR-0006 成本项 |
| 旧 `study-plan-prototype` worktree | 内容未审计 | `legacy-inventory.md` §9 |
