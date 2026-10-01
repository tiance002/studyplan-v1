# 架构决策索引

2026-10-01 / S0。Accepted表示规格决策，不自动表示Implemented/Verified。旧ADR正文保留；新决策声明取代范围，不能将历史文字视为当前产品范围。

| ADR | 当前效力 |
|---|---|
| [0001 独立Git](ADR-0001-independent-git.md) | 保留：D盘正式工程，旧E盘仅参考 |
| [0002 三类状态权威](ADR-0002-three-state-authorities.md) | 保留：业务/断点/Run投影分离 |
| [0003 DB角色隔离](ADR-0003-database-role-isolation.md) | 保留：业务/checkpoint库角色分离 |
| [0004 OpenAPI](ADR-0004-api-contract-openapi.md) | 保留：业务DTO/OpenAPI驱动typed client |
| [0005 LangGraph](ADR-0005-langgraph-single-orchestrator.md) | 部分取代：固定三图/不得第四图由0008取代；单引擎、有界性、授权/幂等/未知不重派继续有效 |
| [0006 开放注册](ADR-0006-auth-policy-open-registration.md) | V1产品注册登录/口令政策由0007取代；原数据和当前代码的认证安全不自动移除 |
| [0007 本地个人入口](ADR-0007-v1-local-user-scope.md) | Accepted，M1.1实现待完成 |
| [0008 工作流/State边界](ADR-0008-workflow-state-boundaries.md) | Accepted，新State/图协议待切片实现；保护旧waiting_user |
| [0009 知识身份/版本来源](ADR-0009-plan-version-learning-context.md) | Accepted，PlanRevision复用；逻辑身份/学习来源待M1.2/M2 |

现有表结构、个人模型配置与checkpoint机制已有代码，不再沿用“待B1决定”的过时列表。正式规格见 [设计入口](../design-package/README.md)，完成度和未核对事项见 [Gap Analysis](../reviews/2026-10-01-v1-gap-analysis.md)。个人RAG部署/License/Adapter能力接入前核对；云端多用户另立未来ADR。
