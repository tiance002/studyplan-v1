# 架构边界

2026-10-01 / S0。依赖方向保持 `API → Application → Domain & Ports ← Infrastructure`，组合根装配实现，Domain 不导入 FastAPI/LangGraph/SDK/SQL。

## 业务职责

catalog 维护逻辑知识身份和内容关系；planning 维护 Proposal、草案、版本、当前路线；resources 维护元数据/章节/偏好；learning/reflections 管会话/原始总结/反馈；practice/progress 管成果/核验/状态；memory 管候选及来源；retrieval/integrations 适配外部证据；ai_gateway 管许可/预算/调用/Attempt，不能决定知识掌握。

这些是职责边界，不要求立即创建全部目录/Service/Graph。先扩展现有模块；跨域命令由 Application 组织事务，避免 PlatformService/AppManager 万能聚合。

## 三类权威与工作流

1. 领域表：计划、学习成果、原始会话、核验与状态的业务事实。
2. checkpoint：运行位置、有限决策和可追溯候选引用。
3. ai_runs：对外授权状态投影；前端只能消费业务 DTO/next_action。

LangGraph 负责有限 Workflow；Planning、Reflection、Practice、Adjustment、Learning 是边界名称，不要求五张空图。现有 planning/summary_review/prompt_review 图复用，普通 CRUD/状态变更用确定性服务。新增图需要独立输入、步数/调用上限、终止与错误边界。

State 目标保存必要 ID、当前批次/索引、预算/manifest hash、有限错误与 pending_decision。完整业务知识树、聊天历史、DB 对象、凭据和大段资料通过授权 Repository/ContextBuilder 获取。当前全量 batches/domain_pack 属已识别设计缺口；后续将候选产物写受限 repository 并以 ID 引用，保留可恢复位置和 ledger。

## 恢复与副作用

现有 `b3f2-batch-v1` waiting_user 包括 Acceptance 09，继续由原 graph_version 和 manifest 恢复；批准/取消不重做生成。State 收缩使用新版本，只作用于新 Run；历史 checkpoint 不覆写、不批量迁移。有限旧版本恢复入口是保全本仓库历史运行，不是兼容旧 E 盘工作流。

外部 dispatch_unknown → reconciliation_required；不自动 retry。已知已完成副作用以 run_id/operation_key 幂等读回，未知结果人工核对。checkpoint 与业务事务分离，恢复要核对 Draft/业务发布结果，不能因 Graph 重放重建计划。

## 检索、模型与客户端

[RAG_DESIGN](RAG_DESIGN.md) 规定唯一检索 Port；[MODEL_ROUTING](MODEL_ROUTING.md) 规定隐私/外发/预算；[MEMORY_CONTEXT](MEMORY_CONTEXT.md) 规定来源和限额。

React 消费 `/api/v1` 的 OpenAPI 业务契约，不理解 provider、prompt、Graph node 或 raw checkpoint。当前路径与 DTO 是运行事实；补充文档举例路径只作为业务能力说明，新增路径由各切片同步 DTO、OpenAPI、fixtures 和 typed client。

PostgreSQL 业务库与 checkpoint 库/角色保持分离，保留既有项目约束、RLS、FK、幂等/lease fencing。V1 本地入口沿用服务端 scope，运行与身份切换见 ADR-0007。

## 错误契约

错误类别 INPUT_ERROR、DOMAIN_ERROR、RETRIEVAL_ERROR、MODEL_ERROR、PROVIDER_ERROR、VALIDATION_ERROR、INFRA_ERROR；与既有 error_class 映射，不能覆盖原因。业务响应包含 code、category、message、request_id 和安全 details；Run 保存阶段/安全失败类别。异常类名可用于 transport 诊断，不暴露密码、API Key、Cookie、Session Token、DSN、Encryption Key。

通用 planning_failed 仅为投影汇总，详细安全原因必须能从受授权业务错误记录核对。此项尚需实现切片补齐，不扩大日志原文或敏感字段。
