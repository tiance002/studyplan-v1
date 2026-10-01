# 学习规划助手 V1：软件设计总入口

2026-10-01 / S0。2026-09-27 V1.1-LG设计由本规格收口版更新；历史正文可从Git读取，历史交付报告不改写。上位输入：[用户补充](supplements/studyplan_requirements_design_supplement_2026-10-01.md)，与旧文档冲突时新规格优先。

## 1. 权威与产品范围

[PRODUCT_SCOPE](PRODUCT_SCOPE.md) 固定个人本地、零基础、首个Agent应用开发领域与完整学习闭环。V1不交付账号产品、SaaS、MCP/Sandbox/Skills Runtime、多Agent自组织、GraphRAG和复杂评分。目标设计与当前实现区分，事实见 [Gap Analysis](../reviews/2026-10-01-v1-gap-analysis.md)。

## 2. 架构与领域契约

[ARCHITECTURE](ARCHITECTURE.md)：API → Application → Domain & Ports ← Infrastructure；业务事实/图断点/Run投影分离；LangGraph有限编排，不承担业务数据库。复用受控worker、ledger、幂等和独立checkpoint库。

[DOMAIN_MODEL](DOMAIN_MODEL.md)：知识逻辑身份、内容版本、PlanRevision承接PlanVersion、版本内关联、六态节点学习事实、单元进度和证据门。现有node_id全量内容hash问题待M1.2；不能将名称稳定当跨版本身份稳定。

[LEARNING_WORKFLOW](LEARNING_WORKFLOW.md)：Plan→Learn→Reflect→Practice→Verify→Adjust；用户先总结/提出实现思路，平台反馈/评审，外部Codex/IDE实施，证据支持实际验收。

## 3. 外部证据、记忆和模型

[RAG_DESIGN](RAG_DESIGN.md)：单一Retrieval Port、受限scope/filter、个人RAG Adapter、引用/版本/Evidence Gate；不重复建设索引引擎。

[MEMORY_CONTEXT](MEMORY_CONTEXT.md)：原事件、导航摘要、结构化记忆、项目事实分离；ContextBuilder有限来源/预算；PROJECT/SESSION先行，长期记忆候选受策略/确认约束。

[MODEL_ROUTING](MODEL_ROUTING.md)：L0确定性、L1按需本地、L2复杂云任务；CallPolicy许可/隐私/预算；无静默云端降级。已验证规划保持19正常/21最大/2repair，unknown进入reconciliation。

## 4. API与客户端

现有运行API在 `/api/v1`，项目范围 `/projects/{project_id}`：生成计划、查询Run/Draft、Draft决定、当前正式路线、workspace；DTO/OpenAPI/typed client是契约事实，补充规格的示例URL不作为已有接口声明。

未来Session/Reflection/Practice/Adjustment业务API在各切片冻结并一起更新schema、OpenAPI、examples、client与测试。AuthContext由服务端本地actor/session adapter构造；不接受客户端自报身份。身份入口改造见ADR-0007，当前代码仍有浏览器认证。

结构发布继续hash+expected_version+幂等键单事务；重复批准不得多发布，编辑后重验；计划失败/取消不改当前正式路线。学习提交追加不可变记录并绑定当时plan/node/content/rubric。

## 5. 恢复、错误与UI

旧waiting_user按原graph_version安全恢复；新State收缩协议只用于新Run。恢复核对领域事务结果，不能因图重放重派付费请求。明确 INPUT/DOMAIN/RETRIEVAL/MODEL/PROVIDER/VALIDATION/INFRA 错误；保留request_id和安全诊断，不输出凭据。

[FRONTEND_INTERACTION](FRONTEND_INTERACTION.md)：11/17/72与N/P/C/A联动、Canvas可用宽度、节点/版本/Session绑定、旧会话恢复、反馈/证据/状态区别。

## 6. 决策与交付

[ADR索引](../adr/README.md) 保留旧决策来源并标明取代关系；[EVALUATION_ACCEPTANCE](EVALUATION_ACCEPTANCE.md) 固定八场景、五危险边界、P0–P3、阶段证据和付费Gate。

本次S0是规格收口；Acceptance09仅Verified到生成/repair/校验/Draft/waiting_user。新身份、六态、Session、反馈、实践核验等实现状态以 [IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md) 为准。
