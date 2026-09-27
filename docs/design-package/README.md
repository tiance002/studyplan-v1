# 设计包

本目录存放 V1.1 的**设计基线**，由用户提供，是实现的权威依据。

| 文件 | 内容 |
|---|---|
| `SOFTWARE_DESIGN.md` | 软件架构与详细设计。含总体架构、模块内聚矩阵、业务实体与约束、三张图、Run/队列/检查点、偏好与资源、API 契约、状态枚举、分级验收、冻结的 ADR |
| `IMPLEMENTATION_PLAN.md` | 实施方案与 B0–B6 里程碑、复用与迁移策略、技术方案、开发顺序 |

## 执行方式

**B0–B6 是独立 Goal，禁止一次性吞下全部批次。** 每个批次的交付要求：
`Goal / Constraints / Allowed changes / Non-goals / Tests / Evidence / Rollback`。

| 批次 | 内容 | 状态 |
|---|---|---|
| B0 | 本机事实审计、隔离与复用清单 | ✅ 完成（`docs/migration/`、`docs/adr/`） |
| B1 | 新骨架、领域契约与 Graph 最小恢复演练 | ✅ 骨架就绪（`docs/acceptance/B1-report.md`） |
| B2 | 知识与计划业务域 | 待开始 |
| B3 | 真实规划 Graph 与云模型 | 待开始 |
| B4 | 资源索引与总结闭环 | 待开始 |
| B5 | 项目实践与 Prompt 工作台后端 | 待开始 |
| B6 | 前后端联调与可交付验收 | 待开始 |

## B1 入口的前置阅读顺序

1. 本目录两份设计文档；
2. `docs/migration/module-reuse-matrix.md`（哪些能复用、哪些禁止迁入）；
3. `docs/adr/`（6 条已冻结决策及其理由）；
4. `docs/acceptance/B1-report.md`（B1 实际交付与 known risks）。

## 冻结时点

B1 结束时应冻结：领域术语、状态枚举、Pydantic 请求/响应、统一错误体、
运行生命周期、Mock 样例、OpenAPI v1。前端可改变展示与布局，
但**不能**自行定义业务状态、Graph 内部节点或自报用户/租户身份。
