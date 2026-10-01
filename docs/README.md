# 文档导航

当前实施入口：2026-10-01 / V2.0；S0和旧V1文档保留未被替换的不变量与历史语义。

## 从哪里开始

| 要做的事 | 阅读入口 |
|---|---|
| 了解项目、目录及当前 develop 状态 | [项目 README](../README.md) |
| 开始开发、核对操作边界 | [AGENTS](../AGENTS.md) → [开发模型路由](execution/README.md) |
| 理解当前需求与设计 | [V2.0指导](implementation/CODEX_GUIDANCE_V2.0.md) → [替代ADR0010](adr/ADR-0010-v2-complete-product-slices.md) → 未被取代的设计包 |
| 判断下一步及已有缺口 | [当前进度](implementation/progress.md) → [F01–F18验收矩阵](implementation/feature-acceptance.md)；旧Gap/实施路线保留作溯源 |
| 核对架构取舍与替代关系 | [ADR 索引](adr/README.md) |
| 配置、启动或执行检查 | [开发说明](development/README.md) → [脚本导航](../scripts/README.md) |
| 核对已完成范围与实际证据 | [验收索引](acceptance/README.md) |

权威顺序以 AGENTS 为准：用户最新明确决定 → V2.0明确替换 → 未被取代的规格/ADR → 实施任务。历史文件保留当时事实，不因文件名或旧报告的完成声明恢复被取代的要求。

## 文件应该放在哪里

| 目录 | 唯一主要用途 | 维护方式 |
|---|---|---|
| `design-package/` | 当前产品、领域、架构和验收规格 | 修改所属专题，其他入口通过链接引用 |
| `implementation/` | V2.0指导原文、连续Goal、唯一当前进度与验收映射 | 原文不改，进度持续更新，避免多份现状说明 |
| `design-package/supplements/` | 用户原始补充要求 | 保留原文字节与来源，不重写 |
| `adr/` | 架构决策及其当前效力 | 新决策明确取代范围，历史正文保留 |
| `development/` | 环境、启动和开发批次边界 | 入口说明适用基线，历史操作说明保留 |
| `execution/` | Codex 开发模型路由及执行约束 | 与产品模型调用规格分开维护 |
| `reviews/` | 差距、基线和问题审查 | 保留日期与被检查基线，不冒充实时状态 |
| `acceptance/` | 验收报告、命令、日志和截图 | 按阶段/批次保留证据与结论 |
| `superpowers/plans/`、`superpowers/specs/` | 既有实施计划和设计讨论 | 属于任务历史，不覆盖正式规格 |
| `migration/` | 旧工程来源、复用及保全记录 | 用于溯源，不授权迁移旧业务数据 |
| `git-maintenance/` | Git 维护前后的事实记录 | 不承担产品实施计划职责 |
| `prototypes/` | 历史视觉参考 | 不作为当前运行产品或已实现声明 |

## 历史资料怎么读

B0–B6、B3-F1/F2 是历史开发批次；当前路线是 M0–M4.5。映射关系只在 [实施路线](design-package/IMPLEMENTATION_PLAN.md) 维护。

以下文件保持原路径，避免破坏旧计划及验收引用：

- [B3 最小实现计划](design-package/B3-minimal-plan.md)、[B3 个人模型设置设计](design-package/B3-user-model-settings-design.md)：历史批次资料。
- [B3-F1 基线审查](reviews/B3-F1-baseline.md)、[旧工程来源](migration/source-provenance.md)：历史事实与来源。
- [B3-F2 分批生成计划](superpowers/plans/2026-09-29-b3f2-batched-generation.md)、[S0 规格收口计划](superpowers/plans/2026-10-01-v1-scope-realignment.md)：任务计划，不是实时完成度。
- `.planning/` 中的执行记录：按任务目录使用；新任务不要覆盖其他任务的计划。

## 避免再次重复

同一个业务规则只在所属专题维护。概览、计划、审查和验收记录链接到规则，并写明自己的基线与核对范围。历史快照即使内容相似，也不作为重复垃圾删除。

新增任务使用明确的目标名；有时间背景的审查/计划使用 `YYYY-MM-DD-主题.md`。证据目录沿用现有批次，不为统一外观重命名历史文件。只涉及导航的调整不改变完成度或里程碑接受状态。
