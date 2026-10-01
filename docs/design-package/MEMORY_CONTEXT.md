# 会话、记忆与上下文

2026-10-01 / S0。目标模块尚未接成产品流程；保留现有总结原文与 rubric 快照基础，见 [审查](../reviews/2026-10-01-v1-gap-analysis.md)。

## 四类数据

| 类别 | 权威/用途 | 保留与来源 |
|---|---|---|
| Raw Conversation | 原始用户/助手事件与工具/反馈结果证据 | 追加 event_id/session_id/time/source；摘要生成不删除原始事件 |
| Summary | 定位导航和有限上下文 | source_event_ids、覆盖范围、版本、生成方式；可回原文，不是新事实源 |
| Structured Memory | 经策略筛选的可引用事实/偏好/决定 | source refs、scope、类型、时间、置信度、用户确认、冲突状态 |
| Project State | 目标、当前路线、进度、成果 | Domain Repository 权威，不能由 memory/summary 覆盖 |

LearningSession 的 plan_version/knowledge identity/content_ref 必须随原始事件保存。消息重试采用客户端幂等键，同键同体同结果、异体冲突；事件排序由服务端确定。

## Scope 与写入

PROJECT/SESSION 为 V1 启用范围，USER 仅预留扩展契约。读取严格限定当前授权 project/session；用户尚未批准的 Memory Candidate 不作为已确认事实。

Conversation → Candidate → Memory Policy → Deduplicate → Conflict Detection → 用户确认（长期决定/敏感内容）→ Persist。模型不能自由写长期记忆。矛盾保留双方来源和时间，明确当前适用/被取代关系；不能用新摘要悄悄覆盖原记录。普通 M2 Session 可先不启用长期记忆后台流程。

## ContextBuilder

输入 current_goal、plan_version、knowledge_node/content/rubric、current_session、recent event refs、relevant memory、retrieval evidence、practice_state、call_policy/token budget。通过受授权 Repository 取有限片段，不拼全量聊天历史/知识树/文档，不复制 DB 对象入 State。

输出有来源标签的有限 ContextPackage、included_source_ids、omitted_source_ids、input token estimate/limit。优先当前目标/用户提交/必要目标和约束，其次近期事件与相关证据；超预算裁剪低优先片段并报告缺口，原文保留。验收所必需的证据/标准不能静默裁掉后仍宣布通过。

本地内容外发检查在 Context 构造前和 provider dispatch 前执行；许可拒绝时不调用云模型。摘要不得提高隐私许可、scope 或证据等级。
