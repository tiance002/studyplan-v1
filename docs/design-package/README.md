# V1 设计包入口

2026-10-01 / S0。权威顺序：用户最新明确决定 → [补充原文](supplements/studyplan_requirements_design_supplement_2026-10-01.md) → 对齐规格/ADR → 实施任务。新补充优先于旧V1.1/B0–B6排期；原验收报告保留为历史。

| 文档 | 唯一主要职责 |
|---|---|
| [PRODUCT_SCOPE](PRODUCT_SCOPE.md) | 个人本地、首个领域、V1/V2与交付目标 |
| [DOMAIN_MODEL](DOMAIN_MODEL.md) | 稳定身份、版本、六态、证据门 |
| [ARCHITECTURE](ARCHITECTURE.md) | 分层、工作流/Repository/State、错误和外部依赖 |
| [LEARNING_WORKFLOW](LEARNING_WORKFLOW.md) | 学习→总结→反馈→实践→验收→调整 |
| [RAG_DESIGN](RAG_DESIGN.md) | 独立RAG边界、检索Evidence、引用和缺证据 |
| [MEMORY_CONTEXT](MEMORY_CONTEXT.md) | 原会话、来源、记忆scope/写入、ContextBuilder |
| [MODEL_ROUTING](MODEL_ROUTING.md) | L0/L1/L2、许可/隐私/预算、失败边界 |
| [FRONTEND_INTERACTION](FRONTEND_INTERACTION.md) | N/P/C/A、节点/版本/Session联动 |
| [EVALUATION_ACCEPTANCE](EVALUATION_ACCEPTANCE.md) | 八场景、证据等级、P0–P3、付费Gate |
| [SOFTWARE_DESIGN](SOFTWARE_DESIGN.md) | 总体设计导航与公共契约 |
| [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) | B0–B6历史映射与M0–M4.5剩余任务 |

[ADR索引](../adr/README.md)、[Gap Analysis](../reviews/2026-10-01-v1-gap-analysis.md)、根AGENTS是执行入口。新文档是目标设计，不等于代码已实现。

当前：B0/B1骨架、B2业务/版本、B3模型、B3-F1前端与B3-F2真实生成已有证据；Acceptance09Verified到waiting_user。本次真实Draft批准/正式发布、Session/总结反馈、成果核验和完整V1闭环尚待验收。下一实现切片M1.1本地身份入口，M1.2稳定知识连接点。

本目录B3-minimal-plan/B3-user-model-settings-design及既有superpowers计划记录历史批次边界；可参考已实施契约，不能覆盖新范围。每个业务Goal独立交付与验证，不一次执行所有里程碑。
