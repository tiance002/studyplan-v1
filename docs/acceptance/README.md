# 验收记录索引

报告是指定基线、指定输入和指定核对范围的证据。历史结果不自动证明当前代码或完整 V1 闭环已经通过；Implemented、Tested、Integrated、Verified 分别记录，测试状态使用 PASS / FAIL / NOT RUN。

## 当前 V1 入口

| 记录 | 可支持的结论 |
|---|---|
| [S0 规格收口](S0-spec-freeze-report.md) | 需求与设计文档收口，后续业务实现仍按实施路线交付 |
| [Acceptance09 真实生成](b3f2/real-provider/2026-10-01-run09-result.md) | 真实生成、repair、校验、Draft / waiting_user；不能推导本次真实批准、发布或完整学习闭环 |
| [真实 provider 批次索引](b3f2/real-provider/README.md) | 各次独立授权与实际结果的历史记录 |

M1.1 的实现与报告在独立功能分支，不由本索引宣称已集成到 develop。

## 历史交付与验证

| 批次 | 报告入口 |
|---|---|
| B1 骨架与边界 | [B1](B1-report.md) |
| B2 业务和发布 | [B2-C](B2-C-report.md)、[B2-V](B2-V-report.md)、[定向验证](B2-V-targeted-report.md) |
| B3 模型与配置 | [最小模型能力](B3-minimal-report.md)、[个人模型设置](B3-personal-model-settings-report.md) |
| B3-F1 正式前端 | [前端交付报告](B3-F1-report.md) |
| B3-F2 汇总 | [交付审查](b3f2/Delivery-audit.md)、[集成记录](b3f2/M0-integration.md) |
| B3-F2 分批生成 | [分批交付](b3f2/batched/Delivery.md)、[命令与结果](b3f2/batched/commands-and-status.md) |
| B3-F2 加固 | [回归](b3f2/hardening/Regression.md)、[真实调用准备](b3f2/hardening/Real-provider-readiness.md) |

## 证据存放规则

本目录的日志、截图、Run 与 usage 文件均保留对应批次和来源。相同内容的日志可能分别属于两个验证批次，不能仅凭哈希相同合并证据。已有 live journal、历史 Attempt 与 unknown 状态不纳入目录清理。

本机临时报告见 [输出目录](../../output/README.md)。正式新验收使用新的批次目录，避免覆盖旧证据；真实 provider 测试每次先按 AGENTS 核对新授权与新 AcceptanceId。
